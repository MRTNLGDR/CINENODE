from __future__ import annotations

from typing import Any
import asyncio

from .engines.registry import EngineRegistry
from .events import EventBus
from .nodes import NodeRegistry
from .store import Store
from .util import now_iso
from .workflow import compile_workflow, node_cache_key, resolve_inputs

TERMINAL={"SUCCEEDED","FAILED","CANCELLED"}


class StopRequested(Exception):
    pass


class JobService:
    def __init__(self,store: Store,nodes: NodeRegistry,engines: EngineRegistry,events: EventBus):
        self.store=store; self.nodes=nodes; self.engines=engines; self.events=events
        self.queue: asyncio.Queue[str]=asyncio.Queue(); self.worker: asyncio.Task[None] | None=None
        self.stop_reasons: dict[str,str]={}; self.active_job: str | None=None

    async def start(self) -> None:
        if self.worker is None or self.worker.done():
            self.worker=asyncio.create_task(self._loop(),name="cinenode-job-worker")
        # Jobs interrupted by a previous process are explicitly resumable.
        with self.store.db.transaction() as con:
            con.execute("UPDATE jobs SET status='INTERRUPTED',stop_reason='process-restart',updated_at=? WHERE status='RUNNING'",(now_iso(),))

    async def stop(self) -> None:
        if self.active_job:
            self.stop_reasons[self.active_job]="shutdown"
        if self.worker:
            self.worker.cancel()
            try: await self.worker
            except asyncio.CancelledError: pass
            self.worker=None
        if self.active_job:
            try: self.store.set_job(self.active_job,"INTERRUPTED",stop_reason="shutdown")
            except KeyError: pass
            self.active_job=None

    async def submit(self,workflow_id: str,payload: dict[str,Any]) -> dict[str,Any]:
        self.store.get_workflow(workflow_id)
        job=self.store.create_job(workflow_id,payload); await self.queue.put(job["id"]); return job

    async def resume(self,job_id: str) -> dict[str,Any]:
        job=self.store.get_job(job_id)
        if job["status"] not in {"INTERRUPTED","FAILED"}: raise ValueError("only interrupted or failed jobs may be resumed")
        self.store.set_job(job_id,"QUEUED",error_code=None,error_message=None,stop_reason=None)
        await self.queue.put(job_id); return self.store.get_job(job_id)

    def cancel(self,job_id: str) -> dict[str,Any]:
        job=self.store.get_job(job_id)
        if job["status"] in TERMINAL: return job
        self.stop_reasons[job_id]="user"
        if job["status"]=="QUEUED": self.store.set_job(job_id,"CANCELLED",stop_reason="user",finished_at=now_iso())
        return self.store.get_job(job_id)

    async def _loop(self) -> None:
        while True:
            job_id=await self.queue.get()
            try: await self._run(job_id)
            except asyncio.CancelledError: raise
            except Exception as exc:
                try: self.store.set_job(job_id,"FAILED",error_code="JOB_FAILED",error_message=str(exc),finished_at=now_iso())
                except KeyError: pass
            finally: self.queue.task_done()

    def _check_stop(self,job_id: str) -> None:
        if job_id in self.stop_reasons: raise StopRequested(self.stop_reasons[job_id])

    async def _run(self,job_id: str) -> None:
        job=self.store.get_job(job_id)
        if job["status"] == "CANCELLED":
            self.stop_reasons.pop(job_id, None)
            return
        workflow=self.store.get_workflow(job["workflow_id"]); compiled=compile_workflow(workflow["definition"],self.nodes)
        outputs=self.store.completed_node_outputs(job_id); self.active_job=job_id
        self.store.set_job(job_id,"RUNNING",started_at=job.get("started_at") or now_iso(),stop_reason=None)
        await self.events.publish(f"job:{job_id}",{"type":"job.started","job_id":job_id})
        try:
            for node_id in compiled.order:
                if node_id in outputs: continue
                self._check_stop(job_id)
                node=compiled.nodes[node_id]; spec=self.nodes.get(str(node["type"])); inputs=resolve_inputs(node,outputs,job["input"])
                self.store.set_job(job_id,"RUNNING",current_node_id=node_id)
                self.store.set_node_run(job_id,node_id,"RUNNING",inputs)
                key=node_cache_key(node,inputs); value=self.store.cache_get(key) if spec.cacheable else None
                if value is None:
                    value=await self._execute(spec.type,spec.handler,node.get("params",{}) or {},inputs)
                    self._check_stop(job_id)
                    if spec.cacheable: self.store.cache_put(key,value)
                outputs[node_id]=value; self.store.set_node_run(job_id,node_id,"SUCCEEDED",inputs,value)
                await self.events.publish(f"job:{job_id}",{"type":"node.succeeded","job_id":job_id,"node_id":node_id})
            result=outputs[compiled.order[-1]]
            self.store.set_job(job_id,"SUCCEEDED",output_json=result,current_node_id=None,finished_at=now_iso())
            await self.events.publish(f"job:{job_id}",{"type":"job.succeeded","job_id":job_id})
        except StopRequested as exc:
            reason=str(exc)
            status="CANCELLED" if reason=="user" else "INTERRUPTED"
            self.store.set_job(job_id,status,stop_reason=reason,finished_at=now_iso() if status=="CANCELLED" else None)
        finally:
            self.stop_reasons.pop(job_id,None); self.active_job=None

    async def _execute(self,node_type: str,handler: Any,params: dict[str,Any],inputs: dict[str,Any]) -> Any:
        if handler is not None: return await handler(params,inputs)
        if node_type=="inference.chat":
            return await self.engines.get(str(params.get("engine","ollama"))).chat(str(inputs.get("prompt","")),params)
        if node_type=="inference.comfyui":
            return await self.engines.get(str(params.get("engine","comfyui"))).run_workflow(inputs.get("workflow") or params.get("workflow") or {},params)
        if node_type=="output.text_file":
            name=str(params.get("name","output.txt")).replace("/","_").replace("\\","_")
            target=(self.store.home/"assets"/"outputs"/name).resolve(); target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text(str(inputs.get("input","")),encoding="utf-8")
            asset=self.store.register_asset(target,project_id=None,job_id=None,kind="text",original_name=name,media_type="text/plain")
            return {"asset_id":asset["id"],"path":asset["relative_path"]}
        raise ValueError(f"node {node_type} has no executor")
