from __future__ import annotations

from cinenode.db import Database


def test_running_jobs_become_interrupted_without_becoming_cancelled(settings):
    settings.ensure()
    db = Database(settings.db_path)
    db.initialize()
    project = db.create_project("p")
    workflow = db.create_workflow(project["id"], "w", {"version": 1, "nodes": [], "edges": [], "metadata": {}})
    job = db.create_job(workflow["id"], {})
    db.set_job_state(job["id"], "RUNNING", current_node_id="node-a")
    assert db.mark_abandoned_interrupted() == 1
    restored = db.get_job(job["id"])
    assert restored["status"] == "INTERRUPTED"
    assert restored["error_code"] == "PROCESS_INTERRUPTED"
    assert restored["cancel_requested"] is False
    assert db.reset_for_resume(job["id"]) is True
    assert db.get_job(job["id"])["status"] == "QUEUED"
