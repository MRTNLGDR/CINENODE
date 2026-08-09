from __future__ import annotations

from pathlib import Path
import json
import textwrap

ROOT = Path(__file__).resolve().parents[1]


def write(path: str, value: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(textwrap.dedent(value).lstrip("\n"), encoding="utf-8", newline="\n")


# This patch is versioned and idempotent. It applies even when an earlier verification file exists.
write(
    "src/cinenode/jobs.py",
    r'''
    from __future__ import annotations

    from typing import Any
    import asyncio

    from .engines.registry import EngineRegistry
    from .events import EventBus
    from .nodes import NodeRegistry
    from .store import Store
    from .util import now_iso
    from .workflow import compile_workflow, node_cache_key, resolve_inputs

    TERMINAL = {"SUCCEEDED", "FAILED", "CANCELLED"}


    class StopRequested(Exception):
        pass


    class JobService:
        """Single-process durable worker.

        Completed node outputs are persisted. User cancellation and process interruption are
        intentionally different states: CANCELLED is terminal, INTERRUPTED is resumable.
        """

        def __init__(self, store: Store, nodes: NodeRegistry, engines: EngineRegistry, events: EventBus):
            self.store = store
            self.nodes = nodes
            self.engines = engines
            self.events = events
            self.queue: asyncio.Queue[str] = asyncio.Queue()
            self.worker: asyncio.Task[None] | None = None
            self.stop_reasons: dict[str, str] = {}
            self.active_job: str | None = None

        async def start(self) -> None:
            # Any RUNNING row left by a crashed process is resumable, never silently failed.
            with self.store.db.transaction() as con:
                con.execute(
                    "UPDATE jobs SET status='INTERRUPTED',stop_reason='process-restart',updated_at=? "
                    "WHERE status='RUNNING'",
                    (now_iso(),),
                )
            if self.worker is None or self.worker.done():
                self.worker = asyncio.create_task(self._loop(), name="cinenode-job-worker")

        async def stop(self) -> None:
            active = self.active_job
            if active:
                self.stop_reasons[active] = "shutdown"
            worker = self.worker
            self.worker = None
            if worker:
                worker.cancel()
                try:
                    await worker
                except asyncio.CancelledError:
                    pass
            if active:
                try:
                    job = self.store.get_job(active)
                    if job["status"] == "RUNNING":
                        self.store.set_job(active, "INTERRUPTED", stop_reason="shutdown")
                        await self.events.publish(
                            f"job:{active}", {"type": "job.interrupted", "job_id": active, "reason": "shutdown"}
                        )
                except KeyError:
                    pass
                finally:
                    self.stop_reasons.pop(active, None)
            self.active_job = None

        async def submit(self, workflow_id: str, payload: dict[str, Any]) -> dict[str, Any]:
            self.store.get_workflow(workflow_id)
            job = self.store.create_job(workflow_id, payload)
            await self.queue.put(job["id"])
            return job

        async def resume(self, job_id: str) -> dict[str, Any]:
            job = self.store.get_job(job_id)
            if job["status"] not in {"INTERRUPTED", "FAILED"}:
                raise ValueError("only interrupted or failed jobs may be resumed")
            self.stop_reasons.pop(job_id, None)
            self.store.set_job(
                job_id,
                "QUEUED",
                error_code=None,
                error_message=None,
                stop_reason=None,
                finished_at=None,
            )
            await self.queue.put(job_id)
            return self.store.get_job(job_id)

        def cancel(self, job_id: str) -> dict[str, Any]:
            job = self.store.get_job(job_id)
            if job["status"] in TERMINAL:
                return job
            self.stop_reasons[job_id] = "user"
            if job["status"] in {"QUEUED", "INTERRUPTED"}:
                self.store.set_job(job_id, "CANCELLED", stop_reason="user", finished_at=now_iso())
            return self.store.get_job(job_id)

        async def _loop(self) -> None:
            while True:
                job_id = await self.queue.get()
                try:
                    await self._run(job_id)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    try:
                        self.store.set_job(
                            job_id,
                            "FAILED",
                            error_code="JOB_FAILED",
                            error_message=str(exc),
                            finished_at=now_iso(),
                        )
                    except KeyError:
                        pass
                finally:
                    self.queue.task_done()

        def _check_stop(self, job_id: str) -> None:
            reason = self.stop_reasons.get(job_id)
            if reason:
                raise StopRequested(reason)

        async def _run(self, job_id: str) -> None:
            job = self.store.get_job(job_id)
            if job["status"] == "CANCELLED":
                self.stop_reasons.pop(job_id, None)
                return
            workflow = self.store.get_workflow(job["workflow_id"])
            compiled = compile_workflow(workflow["definition"], self.nodes)
            outputs = self.store.completed_node_outputs(job_id)
            self.active_job = job_id
            self.store.set_job(
                job_id,
                "RUNNING",
                started_at=job.get("started_at") or now_iso(),
                stop_reason=None,
                finished_at=None,
            )
            await self.events.publish(f"job:{job_id}", {"type": "job.started", "job_id": job_id})
            try:
                for node_id in compiled.order:
                    if node_id in outputs:
                        continue
                    self._check_stop(job_id)
                    node = compiled.nodes[node_id]
                    spec = self.nodes.get(str(node["type"]))
                    inputs = resolve_inputs(node, outputs, job["input"])
                    self.store.set_job(job_id, "RUNNING", current_node_id=node_id)
                    self.store.set_node_run(job_id, node_id, "RUNNING", inputs)
                    key = node_cache_key(node, inputs)
                    value = self.store.cache_get(key) if spec.cacheable else None
                    if value is None:
                        value = await self._execute(spec.type, spec.handler, node.get("params", {}) or {}, inputs)
                        self._check_stop(job_id)
                        if spec.cacheable:
                            self.store.cache_put(key, value)
                    outputs[node_id] = value
                    self.store.set_node_run(job_id, node_id, "SUCCEEDED", inputs, value)
                    await self.events.publish(
                        f"job:{job_id}",
                        {"type": "node.succeeded", "job_id": job_id, "node_id": node_id},
                    )
                result = outputs[compiled.order[-1]]
                self.store.set_job(
                    job_id,
                    "SUCCEEDED",
                    output_json=result,
                    current_node_id=None,
                    finished_at=now_iso(),
                )
                await self.events.publish(f"job:{job_id}", {"type": "job.succeeded", "job_id": job_id})
            except StopRequested as exc:
                reason = str(exc)
                status = "CANCELLED" if reason == "user" else "INTERRUPTED"
                self.store.set_job(
                    job_id,
                    status,
                    stop_reason=reason,
                    finished_at=now_iso() if status == "CANCELLED" else None,
                )
            finally:
                self.stop_reasons.pop(job_id, None)
                if self.active_job == job_id:
                    self.active_job = None

        async def _execute(
            self,
            node_type: str,
            handler: Any,
            params: dict[str, Any],
            inputs: dict[str, Any],
        ) -> Any:
            if handler is not None:
                return await handler(params, inputs)
            if node_type == "inference.chat":
                return await self.engines.get(str(params.get("engine", "ollama"))).chat(
                    str(inputs.get("prompt", "")), params
                )
            if node_type == "inference.comfyui":
                return await self.engines.get(str(params.get("engine", "comfyui"))).run_workflow(
                    inputs.get("workflow") or params.get("workflow") or {}, params
                )
            if node_type == "output.text_file":
                name = str(params.get("name", "output.txt")).replace("/", "_").replace("\\", "_")
                target = (self.store.home / "assets" / "outputs" / name).resolve()
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(str(inputs.get("input", "")), encoding="utf-8")
                asset = self.store.register_asset(
                    target,
                    project_id=None,
                    job_id=None,
                    kind="text",
                    original_name=name,
                    media_type="text/plain",
                )
                return {"asset_id": asset["id"], "path": asset["relative_path"]}
            raise ValueError(f"node {node_type} has no executor")
    ''',
)

write(
    "src/cinenode/capabilities.py",
    r'''
    from __future__ import annotations

    from importlib.util import find_spec
    from typing import Any
    import platform
    import shutil
    import sys


    def detect() -> dict[str, Any]:
        python_modules = {
            name: find_spec(name) is not None
            for name in ("numpy", "PIL", "cv2", "onnxruntime", "torch", "trimesh", "mediapipe")
        }
        executables = {
            name: shutil.which(name)
            for name in ("ffmpeg", "git", "node", "ollama", "nvidia-smi", "docker")
        }
        return {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "modules": python_modules,
            "executables": executables,
            "core_ready": True,
            "local_inference_ready": bool(executables["ollama"] or python_modules["onnxruntime"] or python_modules["torch"]),
        }
    ''',
)

# Insert the capability endpoint without introducing global state.
api = ROOT / "src/cinenode/api/app.py"
source = api.read_text(encoding="utf-8")
if "from cinenode.capabilities import detect as detect_capabilities" not in source:
    source = source.replace(
        "from cinenode.backup import BackupService\n",
        "from cinenode.backup import BackupService\nfrom cinenode.capabilities import detect as detect_capabilities\n",
    )
if 'async def capabilities()' not in source:
    marker = '    @app.get("/api/config")\n'
    addition = '''    @app.get("/api/capabilities")\n    async def capabilities() -> dict[str, Any]:\n        return detect_capabilities()\n\n'''
    source = source.replace(marker, addition + marker)
api.write_text(source, encoding="utf-8")

# Server-mode browsers can store a token locally; local mode remains zero-configuration.
write(
    "src/cinenode/web/api.js",
    r'''
    export class Api {
      token() { return localStorage.getItem("cinenodeToken") || ""; }
      setToken(value) { value ? localStorage.setItem("cinenodeToken", value) : localStorage.removeItem("cinenodeToken"); }
      async request(path, options = {}) {
        const token = this.token();
        const headers = {"Content-Type": "application/json", ...(token ? {"X-CineNode-Token": token} : {}), ...(options.headers || {})};
        const response = await fetch(path, {...options, headers});
        if (response.status === 401 && !options._retried) {
          const supplied = prompt("CineNode server token");
          if (supplied) { this.setToken(supplied); return this.request(path, {...options, _retried: true}); }
        }
        if (!response.ok) { const body = await response.text(); throw new Error(`${response.status}: ${body}`); }
        const type = response.headers.get("content-type") || "";
        return type.includes("application/json") ? response.json() : response.text();
      }
      health(){return this.request("/api/health")} nodes(){return this.request("/api/nodes")} projects(){return this.request("/api/projects")}
      createProject(payload){return this.request("/api/projects",{method:"POST",body:JSON.stringify(payload)})}
      workflows(projectId){return this.request(`/api/workflows${projectId?`?project_id=${encodeURIComponent(projectId)}`:""}`)}
      createWorkflow(payload){return this.request("/api/workflows",{method:"POST",body:JSON.stringify(payload)})}
      updateWorkflow(id,definition){return this.request(`/api/workflows/${id}`,{method:"PUT",body:JSON.stringify({definition})})}
      jobs(){return this.request("/api/jobs")} run(workflowId,input={}){return this.request("/api/jobs",{method:"POST",body:JSON.stringify({workflow_id:workflowId,input})})}
    }
    ''',
)

write(
    "tests/test_recovery.py",
    r'''
    from pathlib import Path
    import time

    from fastapi.testclient import TestClient

    from cinenode.api.app import create_app
    from cinenode.config import Settings


    def _wait(client: TestClient, job_id: str, expected: set[str], timeout: float = 4.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            job = client.get(f"/api/jobs/{job_id}").json()
            if job["status"] in expected:
                return job
            time.sleep(0.02)
        raise AssertionError(f"job did not reach {expected}")


    def test_shutdown_marks_running_job_interrupted_and_resume_reuses_state(tmp_path: Path):
        settings = Settings(home=tmp_path / "runtime", test_mode=True)
        first = create_app(settings)
        with TestClient(first) as client:
            project = client.post("/api/projects", json={"name": "Recovery"}).json()
            definition = {
                "nodes": [
                    {"id": "a", "type": "input.text", "params": {"text": "saved"}},
                    {
                        "id": "b",
                        "type": "control.delay",
                        "inputs": {"input": {"node": "a"}},
                        "params": {"seconds": 1.0},
                    },
                    {
                        "id": "c",
                        "type": "transform.template",
                        "inputs": {"input": {"node": "b"}},
                        "params": {"template": "{input}-resumed"},
                    },
                ]
            }
            workflow = client.post(
                "/api/workflows",
                json={"project_id": project["id"], "name": "Resume", "definition": definition},
            ).json()
            job = client.post("/api/jobs", json={"workflow_id": workflow["id"], "input": {}}).json()
            _wait(client, job["id"], {"RUNNING"})

        second = create_app(settings)
        with TestClient(second) as client:
            interrupted = client.get(f"/api/jobs/{job['id']}").json()
            assert interrupted["status"] == "INTERRUPTED"
            assert interrupted["stop_reason"] == "shutdown"
            response = client.post(f"/api/jobs/{job['id']}/resume")
            assert response.status_code == 200
            completed = _wait(client, job["id"], {"SUCCEEDED"}, timeout=5.0)
            assert completed["output"] == "saved-resumed"


    def test_import_has_no_runtime_side_effects(tmp_path: Path, monkeypatch):
        target = tmp_path / "import-only"
        monkeypatch.setenv("CINENODE_HOME", str(target))
        __import__("cinenode")
        assert not target.exists()
    ''',
)

write(
    "docs/RECOVERY.md",
    r'''
    # Recovery contract

    A user cancellation is terminal (`CANCELLED`). A process close, restart or crash is resumable
    (`INTERRUPTED`). Node outputs are committed individually, so resuming skips nodes already marked
    `SUCCEEDED` and re-executes only the interrupted node and its remaining dependents.

    Backups use logical paths relative to `CINENODE_HOME`, include a consistent SQLite snapshot and
    verify every archived file by size and SHA-256 before restoring into another directory or machine.
    ''',
)

# Versioned patch marker is included in the source manifest.
write(
    "docs/PATCH_LEVEL.json",
    json.dumps(
        {
            "product": "CineNode",
            "patch_level": 2,
            "contracts": [
                "interrupted jobs are resumable",
                "imports have no filesystem side effects",
                "server web client supports explicit token",
                "local capability diagnostics are exposed",
            ],
        },
        indent=2,
    )
    + "\n",
)

print("CineNode patch v2 applied")
