export class Api {
  async request(path, options = {}) {
    const response = await fetch(path, {headers: {"Content-Type": "application/json", ...(options.headers || {})}, ...options});
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
