from __future__ import annotations


def empty_graph():
    return {"version": 1, "nodes": [], "edges": [], "metadata": {}}


def test_project_crud_and_persistence(client):
    created = client.post("/api/projects", json={"name": "Filme A", "description": "teste", "graph": empty_graph()})
    assert created.status_code == 201
    project = created.json()
    fetched = client.get(f"/api/projects/{project['id']}").json()
    assert fetched["name"] == "Filme A"
    updated = client.put(f"/api/projects/{project['id']}", json={"name": "Filme B"})
    assert updated.status_code == 200
    assert updated.json()["name"] == "Filme B"
    assert any(item["id"] == project["id"] for item in client.get("/api/projects").json()["items"])
    assert client.delete(f"/api/projects/{project['id']}").status_code == 204
    assert client.get(f"/api/projects/{project['id']}").status_code == 404


def test_cycle_and_dangling_edges_are_rejected(client):
    graph = {
        "version": 1,
        "nodes": [
            {"id": "a", "type": "input.text", "position": {"x": 0, "y": 0}, "config": {"text": "a"}},
            {"id": "b", "type": "output.preview", "position": {"x": 100, "y": 0}, "config": {}},
        ],
        "edges": [
            {"id": "e1", "source": "a", "target": "b"},
            {"id": "e2", "source": "b", "target": "a"},
            {"id": "e3", "source": "missing", "target": "a"},
        ],
        "metadata": {},
    }
    payload = client.post("/api/workflows/validate", json=graph).json()
    assert payload["valid"] is False
    codes = {item["code"] for item in payload["errors"]}
    assert "WORKFLOW_CYCLE" in codes
    assert "DANGLING_EDGE" in codes


def test_unknown_node_type_is_rejected(client):
    graph = {"version": 1, "nodes": [{"id": "x", "type": "fake.node", "position": {"x": 0, "y": 0}, "config": {}}], "edges": [], "metadata": {}}
    payload = client.post("/api/workflows/validate", json=graph).json()
    assert payload["valid"] is False
    assert payload["errors"][0]["code"] == "UNKNOWN_NODE_TYPE"
