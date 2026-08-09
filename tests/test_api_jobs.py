import time


def create_workflow(client, seconds=0):
    project=client.post("/api/projects",json={"name":"Movie"}).json()
    definition={"nodes":[{"id":"a","type":"input.text","params":{"text":"hello"}},{"id":"b","type":"control.delay","inputs":{"input":{"node":"a"}},"params":{"seconds":seconds}},{"id":"c","type":"transform.template","inputs":{"input":{"node":"b"}},"params":{"template":"{input} world"}}]}
    response=client.post("/api/workflows",json={"project_id":project["id"],"name":"Test","definition":definition}); assert response.status_code==201
    return response.json()


def wait_job(client,job_id):
    for _ in range(100):
        item=client.get(f"/api/jobs/{job_id}").json()
        if item["status"] in {"SUCCEEDED","FAILED","CANCELLED","INTERRUPTED"}: return item
        time.sleep(.03)
    raise AssertionError("job timed out")


def test_health_catalog_and_crud(client):
    assert client.get("/api/health").json()["product"]=="CineNode"
    assert any(item["type"]=="inference.chat" for item in client.get("/api/nodes").json())
    workflow=create_workflow(client)
    updated=client.put(f"/api/workflows/{workflow['id']}",json={"definition":workflow["definition"]}); assert updated.status_code==200; assert updated.json()["revision"]==2


def test_job_executes_and_cache_is_persistent(client):
    workflow=create_workflow(client)
    first=client.post("/api/jobs",json={"workflow_id":workflow["id"],"input":{}}).json(); result=wait_job(client,first["id"])
    assert result["status"]=="SUCCEEDED"; assert result["output"]=="hello world"
    second=client.post("/api/jobs",json={"workflow_id":workflow["id"],"input":{}}).json(); assert wait_job(client,second["id"])["status"]=="SUCCEEDED"


def test_queued_or_running_job_can_be_cancelled(client):
    workflow=create_workflow(client,.4)
    job=client.post("/api/jobs",json={"workflow_id":workflow["id"],"input":{}}).json(); client.post(f"/api/jobs/{job['id']}/cancel")
    assert wait_job(client,job["id"])["status"]=="CANCELLED"


def test_upload_is_streamed_and_downloadable(client):
    response=client.post("/api/assets/upload",files={"upload":("hello.txt",b"hello","text/plain")}); assert response.status_code==201
    asset=response.json(); download=client.get(f"/api/assets/{asset['id']}"); assert download.content==b"hello"
