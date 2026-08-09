from __future__ import annotations

import queue
import threading
from typing import Any

from .config import Settings
from .db import Database
from .schemas import WorkflowGraph
from .workflow import ExecutionContext, JobCancelled, WorkflowError, execute_graph


class JobManager:
    def __init__(self, settings: Settings, db: Database):
        self.settings = settings
        self.db = db
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []
        self._queued: set[str] = set()
        self._lock = threading.RLock()

    def start(self) -> None:
        self.db.mark_abandoned_interrupted()
        if self._threads:
            return
        self._stop.clear()
        for index in range(self.settings.job_workers):
            thread = threading.Thread(target=self._worker, name=f"cinenode-job-{index + 1}", daemon=True)
            thread.start()
            self._threads.append(thread)
        for job in reversed(self.db.list_jobs(limit=500)):
            if job["status"] == "QUEUED":
                self.enqueue(job["id"])

    def shutdown(self, timeout: float = 15.0) -> None:
        self._stop.set()
        for _ in self._threads:
            self._queue.put(None)
        for thread in self._threads:
            thread.join(timeout=timeout)
        self._threads.clear()

    def enqueue(self, job_id: str) -> None:
        with self._lock:
            if job_id in self._queued:
                return
            self._queued.add(job_id)
            self._queue.put(job_id)

    def create_and_enqueue(self, workflow_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
        job = self.db.create_job(workflow_id, inputs)
        self.enqueue(job["id"])
        return job

    def resume(self, job_id: str) -> dict[str, Any] | None:
        if not self.db.reset_for_resume(job_id):
            return None
        self.db.add_event(job_id, "resumed", {})
        self.enqueue(job_id)
        return self.db.get_job(job_id)

    def _event(self, job_id: str, kind: str, payload: dict[str, Any]) -> None:
        self.db.add_event(job_id, kind, payload)

    def _worker(self) -> None:
        while not self._stop.is_set():
            job_id = self._queue.get()
            if job_id is None:
                self._queue.task_done()
                return
            with self._lock:
                self._queued.discard(job_id)
            try:
                self._run(job_id)
            finally:
                self._queue.task_done()

    def _run(self, job_id: str) -> None:
        job = self.db.get_job(job_id)
        if not job or job["status"] != "QUEUED":
            return
        workflow = self.db.get_workflow(job["workflow_id"])
        if not workflow:
            self.db.set_job_state(job_id, "FAILED", error_code="WORKFLOW_NOT_FOUND", error_message="Workflow removido")
            self._event(job_id, "failed", {"code": "WORKFLOW_NOT_FOUND"})
            return
        self.db.set_job_state(job_id, "RUNNING")
        self._event(job_id, "running", {"workflow_id": workflow["id"]})
        context = ExecutionContext(
            settings=self.settings,
            db=self.db,
            job_id=job_id,
            project_id=workflow["project_id"],
            run_inputs=job["inputs"],
            cancelled=lambda: self._stop.is_set() or self.db.cancel_requested(job_id),
            event=lambda kind, payload: self._event(job_id, kind, payload),
        )
        try:
            result = execute_graph(WorkflowGraph.model_validate(workflow["graph"]), context)
            if self._stop.is_set() and not self.db.cancel_requested(job_id):
                self.db.set_job_state(
                    job_id, "INTERRUPTED", error_code="PROCESS_INTERRUPTED",
                    error_message="CineNode foi encerrado antes da conclusão.",
                )
                self._event(job_id, "interrupted", {"reason": "shutdown"})
                return
            self.db.set_job_state(job_id, "SUCCEEDED", result=result, current_node_id=None)
            self._event(job_id, "succeeded", {"outputs": list(result.get("outputs", {}))})
        except JobCancelled as exc:
            if self._stop.is_set() and not self.db.cancel_requested(job_id):
                status, code, kind = "INTERRUPTED", "PROCESS_INTERRUPTED", "interrupted"
            else:
                status, code, kind = "CANCELLED", "JOB_CANCELLED", "cancelled"
            self.db.set_job_state(job_id, status, error_code=code, error_message=str(exc))
            self._event(job_id, kind, {"code": code, "message": str(exc)})
        except WorkflowError as exc:
            if self._stop.is_set() and not self.db.cancel_requested(job_id):
                self.db.set_job_state(job_id, "INTERRUPTED", error_code="PROCESS_INTERRUPTED", error_message=str(exc))
                self._event(job_id, "interrupted", {"node_id": exc.node_id, "message": str(exc)})
            else:
                self.db.set_job_state(job_id, "FAILED", error_code=exc.code, error_message=str(exc), current_node_id=exc.node_id)
                self._event(job_id, "failed", {"code": exc.code, "node_id": exc.node_id, "message": str(exc)})
        except Exception as exc:
            self.db.set_job_state(job_id, "FAILED", error_code="UNEXPECTED_ERROR", error_message=f"{type(exc).__name__}: {exc}")
            self._event(job_id, "failed", {"code": "UNEXPECTED_ERROR", "message": str(exc)})
