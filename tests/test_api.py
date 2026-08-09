from __future__ import annotations

import io
import time


def create_project(client, name="Projeto teste"):
    response = client.post("/api/projects", json={"name": name, "description": ""})
    assert response.status_code == 201, response.text
    return response.json()


def create_sum_workflow(client, project_id):
    graph = {
        "version": 1,
        "metadata": {},
        "nodes": [
            {"id": "a", "type": "input.number", "params": {"value": 2}, "x": 0, "y": 0},
            {"id": "b", "type": "input.number", "params": {"value": 3}, "x": 0, "y": 100},
            {"id": "sum", "type": "math.add", "params": {}, "x": 300, "y": 50},
            {"id": "out", "type": "output.json", "params": {}, "x": 600, "y": 50},
        ],
        "edges": [
            {"id": "e1", "source": "a", "source_port": "value", "target": "sum", "target_port": "a"},
            {"id": "e2", "source": "b", "source_port": "value", "target": "sum", "target_port": "b"},
            {"id": "e3", "source": "sum", "source_port": "value", "target": "out", "target_port": "value"},
        ],
    }
    response = client.post("/api/workflows", json={"project_id": project_id, "name": "Soma", "graph": graph})
    assert response.status_code == 201, response.text
    return response.json()


def wait_job(client, job_id, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in {"SUCCEEDED", "FAILED", "CANCELLED", "INTERRUPTED"}:
            return job
        time.sleep(0.03)
    raise AssertionError("job timeout")


def test_health_and_product_boundary(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["name"] == "CineNode"
    assert body["perzon_bundled"] is False
    assert client.get("/api/perzon/operacoes").status_code == 404


def test_project_workflow_and_real_job_execution(client):
    project = create_project(client)
    workflow = create_sum_workflow(client, project["id"])
    response = client.post(f"/api/workflows/{workflow['id']}/run", json={"inputs": {}})
    assert response.status_code == 202
    job = wait_job(client, response.json()["id"])
    assert job["status"] == "SUCCEEDED", job
    assert job["result"]["outputs"]["out"] == 5.0
    assert any(event["kind"] == "node_succeeded" for event in job["events"])


def test_run_inputs_override_input_node(client):
    project = create_project(client)
    workflow = create_sum_workflow(client, project["id"])
    job_id = client.post(
        f"/api/workflows/{workflow['id']}/run",
        json={"inputs": {"a": 10, "b": {"value": 4}}},
    ).json()["id"]
    job = wait_job(client, job_id)
    assert job["result"]["outputs"]["out"] == 14.0


def test_invalid_cycle_never_enters_database(client):
    project = create_project(client)
    graph = {
        "version": 1,
        "metadata": {},
        "nodes": [
            {"id": "a", "type": "text.concat", "params": {}, "x": 0, "y": 0},
            {"id": "b", "type": "text.concat", "params": {}, "x": 0, "y": 0},
        ],
        "edges": [
            {"id": "e1", "source": "a", "source_port": "text", "target": "b", "target_port": "a"},
            {"id": "e2", "source": "b", "source_port": "text", "target": "a", "target_port": "a"},
        ],
    }
    response = client.post("/api/workflows", json={"project_id": project["id"], "name": "Ciclo", "graph": graph})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_GRAPH"


def test_asset_upload_uses_relative_relocatable_path(client, settings):
    project = create_project(client)
    response = client.post(
        f"/api/assets/upload?project_id={project['id']}",
        files={"file": ("frame.txt", io.BytesIO(b"cinenode"), "text/plain")},
    )
    assert response.status_code == 201, response.text
    asset = response.json()
    assert not asset["relative_path"].startswith("/")
    assert "uploads" in asset["relative_path"]
    downloaded = client.get(f"/api/assets/{asset['id']}")
    assert downloaded.content == b"cinenode"


def test_cancel_delay_job(client):
    project = create_project(client)
    graph = {
        "version": 1,
        "metadata": {},
        "nodes": [
            {"id": "in", "type": "input.text", "params": {"value": "x"}, "x": 0, "y": 0},
            {"id": "delay", "type": "util.delay", "params": {"seconds": 2}, "x": 250, "y": 0},
            {"id": "out", "type": "output.text", "params": {}, "x": 500, "y": 0},
        ],
        "edges": [
            {"id": "e1", "source": "in", "source_port": "value", "target": "delay", "target_port": "value"},
            {"id": "e2", "source": "delay", "source_port": "value", "target": "out", "target_port": "value"},
        ],
    }
    workflow = client.post("/api/workflows", json={"project_id": project["id"], "name": "Delay", "graph": graph}).json()
    job_id = client.post(f"/api/workflows/{workflow['id']}/run", json={"inputs": {}}).json()["id"]
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        if client.get(f"/api/jobs/{job_id}").json()["status"] == "RUNNING":
            break
        time.sleep(0.02)
    response = client.post(f"/api/jobs/{job_id}/cancel")
    assert response.status_code == 202
    job = wait_job(client, job_id)
    assert job["status"] == "CANCELLED"
    assert job["error_code"] == "JOB_CANCELLED"


def test_frontend_is_packaged(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "CineNode" in response.text
    assert client.get("/static/app.js").status_code == 200
