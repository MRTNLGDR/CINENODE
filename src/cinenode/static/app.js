(() => {
  "use strict";
  const q = s => document.querySelector(s);
  const E = Object.fromEntries([
    "projectSelect","workflowSelect","newProjectBtn","newWorkflowBtn","uploadBtn","saveBtn","runBtn","cancelBtn",
    "fileInput","catalog","catalogCount","nodeSearch","engines","refreshEngines","canvasViewport","canvasTransform",
    "nodeLayer","edgeLayer","inspector","selectionType","jobState","jobOutput","jobProgress","statusText","graphStats",
    "emptyHint","fitBtn","clearBtn","versionText","toastRoot"
  ].map(id => [id, q(`#${id}`)]));
  const S = {
    specs:new Map(), catalog:[], projects:[], workflows:[], projectId:null, workflowId:null, workflowName:"Workflow",
    graph:{version:1,nodes:[],edges:[],metadata:{}}, selected:null, pending:null, jobId:null, timer:null,
    panX:40, panY:40, zoom:1, dirty:false
  };
  const esc = v => String(v).replace(/[&<>'"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c]));
  const uid = p => `${p}_${crypto.randomUUID().replaceAll("-","").slice(0,12)}`;
  const node = id => S.graph.nodes.find(n => n.id === id);
  const spec = type => S.specs.get(type);
  const setStatus = text => E.statusText.textContent = text;
  const dirty = value => { S.dirty=value; document.title=`${value?"● ":""}CineNode`; };
  function toast(text, kind="") { const el=document.createElement("div"); el.className=`toast ${kind}`; el.textContent=text; E.toastRoot.append(el); setTimeout(()=>el.remove(),4200); }
  async function api(path, options={}) {
    const r=await fetch(path,options), type=r.headers.get("content-type")||"";
    const body=type.includes("json")?await r.json():await r.text();
    if(!r.ok) throw new Error(body?.error?.message||body?.message||String(body)||`${r.status} ${r.statusText}`);
    return body;
  }
  const jsonOptions = body => ({method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify(body)});
  function transform(){ E.canvasTransform.style.transform=`translate(${S.panX}px,${S.panY}px) scale(${S.zoom})`; }
  function stats(){ E.graphStats.textContent=`${S.graph.nodes.length} nós · ${S.graph.edges.length} conexões`; E.emptyHint.classList.toggle("hidden",!!S.graph.nodes.length); }
  function position(){ const r=E.canvasViewport.getBoundingClientRect(); return {x:Math.max(20,(r.width/2-S.panX)/S.zoom-110),y:Math.max(20,(r.height/2-S.panY)/S.zoom-50)}; }
  function add(type, params, at=position()) {
    const d=spec(type); if(!d) return;
    const n={id:uid("node"),type,x:Math.round(at.x),y:Math.round(at.y),params:structuredClone(params??d.defaults??{})};
    S.graph.nodes.push(n); S.selected=n.id; dirty(true); render(); inspect(); return n;
  }
  function removeSelected(){ if(!S.selected)return; S.graph.nodes=S.graph.nodes.filter(n=>n.id!==S.selected); S.graph.edges=S.graph.edges.filter(e=>e.source!==S.selected&&e.target!==S.selected); S.selected=null; dirty(true); render(); inspect(); }
  function connect(source, source_port, target, target_port){
    if(source===target)return toast("Não é permitido conectar o nó a ele mesmo.","error");
    S.graph.edges=S.graph.edges.filter(e=>!(e.target===target&&e.target_port===target_port));
    S.graph.edges.push({id:uid("edge"),source,source_port,target,target_port}); S.pending=null; dirty(true); render();
  }
  function portY(n, direction, port){ const ports=direction==="output"?spec(n.type).outputs:spec(n.type).inputs; return n.y+50+Math.max(0,ports.indexOf(port))*23; }
  function edges(){
    E.edgeLayer.replaceChildren();
    for(const e of S.graph.edges){ const a=node(e.source),b=node(e.target); if(!a||!b)continue;
      const x1=a.x+220,y1=portY(a,"output",e.source_port),x2=b.x,y2=portY(b,"input",e.target_port),d=Math.max(55,Math.abs(x2-x1)*.45);
      const p=document.createElementNS("http://www.w3.org/2000/svg","path"); p.classList.add("edge-path"); p.setAttribute("d",`M ${x1} ${y1} C ${x1+d} ${y1}, ${x2-d} ${y2}, ${x2} ${y2}`); E.edgeLayer.append(p);
    }
  }
  function renderNode(n){
    const d=spec(n.type), el=document.createElement("article"); el.className=`node ${S.selected===n.id?"selected":""}`; el.style.cssText=`left:${n.x}px;top:${n.y}px`;
    const ports=(items,dir)=>items.map(p=>`<div class="port ${dir} ${S.pending?.nodeId===n.id&&S.pending?.port===p?"pending":""}" data-dir="${dir}" data-port="${esc(p)}">${esc(p)}</div>`).join("");
    el.innerHTML=`<div class="node-header"><span class="node-kind"></span><span class="node-title">${esc(d.label)}</span><span class="node-id">${esc(n.id.slice(-5))}</span></div><div class="node-body"><div class="ports inputs">${ports(d.inputs,"input")}</div><div class="ports outputs">${ports(d.outputs,"output")}</div></div>`;
    el.addEventListener("pointerdown",ev=>{ if(ev.target.closest(".port"))return; S.selected=n.id; render(); inspect(); });
    const head=el.querySelector(".node-header"); head.addEventListener("pointerdown",ev=>{
      ev.preventDefault(); const sx=ev.clientX,sy=ev.clientY,ox=n.x,oy=n.y; head.setPointerCapture(ev.pointerId);
      const move=m=>{ n.x=Math.round(ox+(m.clientX-sx)/S.zoom); n.y=Math.round(oy+(m.clientY-sy)/S.zoom); el.style.left=`${n.x}px`; el.style.top=`${n.y}px`; edges(); dirty(true); };
      const up=()=>{ head.removeEventListener("pointermove",move); head.removeEventListener("pointerup",up); inspect(); };
      head.addEventListener("pointermove",move); head.addEventListener("pointerup",up);
    });
    el.querySelectorAll(".port").forEach(p=>p.addEventListener("pointerdown",ev=>{
      ev.stopPropagation(); const dir=p.dataset.dir,port=p.dataset.port;
      if(dir==="output"){S.pending={nodeId:n.id,port};setStatus(`Escolha uma entrada para ${d.label}.${port}`);render();}
      else if(S.pending){connect(S.pending.nodeId,S.pending.port,n.id,port);setStatus("Conexão criada.");}
    }));
    return el;
  }
  function render(){ E.nodeLayer.replaceChildren(...S.graph.nodes.map(renderNode)); edges(); stats(); transform(); }
  function inspect(){
    const n=node(S.selected); if(!n){E.selectionType.textContent="nenhum";E.inspector.className="inspector empty-inspector";E.inspector.textContent="Selecione um nó no canvas.";return;}
    const d=spec(n.type); E.selectionType.textContent=d.label; E.inspector.className="inspector";
    E.inspector.innerHTML=`<label class="field"><span>ID</span><input value="${esc(n.id)}" disabled></label><label class="field"><span>Tipo</span><input value="${esc(n.type)}" disabled></label><label class="field"><span>Parâmetros JSON</span><textarea id="paramsBox">${esc(JSON.stringify(n.params,null,2))}</textarea></label><div class="field"><span>Descrição</span><small class="muted">${esc(d.description)}</small></div><div class="inspector-actions"><button id="applyParams">Aplicar</button><button id="deleteNode" class="danger">Excluir</button></div>`;
    q("#applyParams").onclick=()=>{try{n.params=JSON.parse(q("#paramsBox").value||"{}");dirty(true);toast("Parâmetros aplicados.","success");}catch(e){toast(`JSON inválido: ${e.message}`,"error");}};
    q("#deleteNode").onclick=removeSelected;
  }
  function renderCatalog(filter=""){
    const groups=new Map(), term=filter.trim().toLowerCase();
    for(const d of S.catalog){if(term&&!`${d.label} ${d.type} ${d.description}`.toLowerCase().includes(term))continue;if(!groups.has(d.category))groups.set(d.category,[]);groups.get(d.category).push(d);}
    E.catalog.innerHTML=[...groups].map(([category,items])=>`<section class="catalog-group"><h3>${esc(category)}</h3>${items.map(d=>`<button class="catalog-item" data-type="${esc(d.type)}"><span class="catalog-icon">${esc(d.label[0])}</span><span class="catalog-copy"><strong>${esc(d.label)}</strong><small>${esc(d.description)}</small></span></button>`).join("")}</section>`).join("");
    E.catalog.querySelectorAll("[data-type]").forEach(b=>b.onclick=()=>add(b.dataset.type));
  }
  async function engines(){ const data=await api("/api/engines"); E.engines.innerHTML=data.engines.map(x=>`<div class="engine-row"><span>${esc(x.id)}</span><span class="engine-dot ${x.available?"ok":""}" title="${esc(x.detail||x.path||"")}"></span></div>`).join(""); }
  async function projects(preferred){
    const data=await api("/api/projects"); S.projects=data.projects;
    if(!S.projects.length){const p=await api("/api/projects",jsonOptions({name:"Meu primeiro projeto",description:""}));return projects(p.id);}
    S.projectId=preferred||S.projectId||S.projects[0].id; if(!S.projects.some(p=>p.id===S.projectId))S.projectId=S.projects[0].id;
    E.projectSelect.innerHTML=S.projects.map(p=>`<option value="${p.id}">${esc(p.name)}</option>`).join("");E.projectSelect.value=S.projectId;await workflows();
  }
  async function workflows(preferred){
    const data=await api(`/api/workflows?project_id=${encodeURIComponent(S.projectId)}`); S.workflows=data.workflows;
    if(!S.workflows.length){const w=await api("/api/workflows",jsonOptions({project_id:S.projectId,name:"Workflow principal",graph:{version:1,nodes:[],edges:[],metadata:{}}}));return workflows(w.id);}
    S.workflowId=preferred||S.workflowId||S.workflows[0].id;if(!S.workflows.some(w=>w.id===S.workflowId))S.workflowId=S.workflows[0].id;
    E.workflowSelect.innerHTML=S.workflows.map(w=>`<option value="${w.id}">${esc(w.name)}</option>`).join("");E.workflowSelect.value=S.workflowId;await load(S.workflowId);
  }
  async function load(id){const w=await api(`/api/workflows/${encodeURIComponent(id)}`);S.workflowId=w.id;S.workflowName=w.name;S.graph=w.graph;S.selected=null;S.pending=null;dirty(false);render();inspect();setStatus(`Workflow carregado: ${w.name}`);}
  async function save(notify=true){
    const v=await api("/api/workflows/validate",jsonOptions(S.graph));if(!v.valid)throw new Error(v.errors.join("; "));
    const w=await api(`/api/workflows/${encodeURIComponent(S.workflowId)}`,{method:"PUT",headers:{"content-type":"application/json"},body:JSON.stringify({name:S.workflowName,graph:S.graph})});S.graph=w.graph;dirty(false);if(notify)toast("Workflow salvo.","success");
  }
  function showJob(j){
    E.jobState.textContent=j?.status||"IDLE";E.jobState.className=`state-pill ${(j?.status||"idle").toLowerCase()}`;
    const events=j?.events||[],done=events.filter(e=>e.kind==="node_succeeded").length,total=events.find(e=>e.kind==="workflow_started")?.payload?.nodes||S.graph.nodes.length||1;E.jobProgress.style.width=`${Math.min(100,done/total*100)}%`;
    E.cancelBtn.disabled=!j||["SUCCEEDED","FAILED","CANCELLED","INTERRUPTED"].includes(j.status);E.jobOutput.textContent=JSON.stringify({id:j?.id,status:j?.status,current_node_id:j?.current_node_id,error:j?.error_message,result:j?.result,events:events.slice(-12)},null,2);
  }
  async function poll(){clearTimeout(S.timer);if(!S.jobId)return;try{const j=await api(`/api/jobs/${encodeURIComponent(S.jobId)}`);showJob(j);if(["SUCCEEDED","FAILED","CANCELLED","INTERRUPTED"].includes(j.status)){toast(`Job ${j.status}${j.error_message?`: ${j.error_message}`:""}`,j.status==="SUCCEEDED"?"success":"error");return;}S.timer=setTimeout(poll,450);}catch(e){E.jobOutput.textContent=e.message;S.timer=setTimeout(poll,1200);}}
  async function run(){try{await save(false);const j=await api(`/api/workflows/${encodeURIComponent(S.workflowId)}/run`,jsonOptions({inputs:{}}));S.jobId=j.id;showJob(j);poll();toast("Workflow iniciado.","success");}catch(e){toast(e.message,"error");}}
  async function upload(file){if(!file)return;const form=new FormData();form.append("file",file);try{const a=await api(`/api/assets/upload?project_id=${encodeURIComponent(S.projectId)}`,{method:"POST",body:form});add("input.file",{asset_id:a.id});toast(`Arquivo enviado: ${a.name}`,"success");}catch(e){toast(e.message,"error");}E.fileInput.value="";}
  function fit(){if(!S.graph.nodes.length){S.panX=40;S.panY=40;S.zoom=1;return transform();}const xs=S.graph.nodes.map(n=>n.x),ys=S.graph.nodes.map(n=>n.y),minX=Math.min(...xs),minY=Math.min(...ys),maxX=Math.max(...xs)+220,maxY=Math.max(...ys)+120,r=E.canvasViewport.getBoundingClientRect();S.zoom=Math.min(1.25,Math.max(.35,Math.min((r.width-80)/(maxX-minX),(r.height-80)/(maxY-minY))));S.panX=(r.width-(maxX-minX)*S.zoom)/2-minX*S.zoom;S.panY=(r.height-(maxY-minY)*S.zoom)/2-minY*S.zoom;transform();}
  function bind(){
    E.nodeSearch.oninput=()=>renderCatalog(E.nodeSearch.value);E.refreshEngines.onclick=()=>engines().catch(e=>toast(e.message,"error"));
    E.projectSelect.onchange=()=>{S.projectId=E.projectSelect.value;S.workflowId=null;workflows();};E.workflowSelect.onchange=()=>load(E.workflowSelect.value);
    E.newProjectBtn.onclick=async()=>{const name=prompt("Nome do projeto:","Novo projeto");if(name?.trim()){const p=await api("/api/projects",jsonOptions({name:name.trim(),description:""}));await projects(p.id);}};
    E.newWorkflowBtn.onclick=async()=>{const name=prompt("Nome do workflow:","Novo workflow");if(name?.trim()){const w=await api("/api/workflows",jsonOptions({project_id:S.projectId,name:name.trim(),graph:{version:1,nodes:[],edges:[],metadata:{}}}));await workflows(w.id);}};
    E.saveBtn.onclick=()=>save().catch(e=>toast(e.message,"error"));E.runBtn.onclick=run;E.cancelBtn.onclick=async()=>{if(S.jobId)await api(`/api/jobs/${encodeURIComponent(S.jobId)}/cancel`,{method:"POST"});};
    E.uploadBtn.onclick=()=>E.fileInput.click();E.fileInput.onchange=()=>upload(E.fileInput.files[0]);E.fitBtn.onclick=fit;E.clearBtn.onclick=()=>{if(confirm("Remover todos os nós?")){S.graph.nodes=[];S.graph.edges=[];S.selected=null;dirty(true);render();inspect();}};
    let pan=null;E.canvasViewport.onpointerdown=e=>{if(e.target.closest(".node"))return;S.selected=null;inspect();pan={x:e.clientX,y:e.clientY,px:S.panX,py:S.panY};E.canvasViewport.setPointerCapture(e.pointerId);};E.canvasViewport.onpointermove=e=>{if(pan){S.panX=pan.px+e.clientX-pan.x;S.panY=pan.py+e.clientY-pan.y;transform();}};E.canvasViewport.onpointerup=()=>pan=null;
    E.canvasViewport.onwheel=e=>{e.preventDefault();const r=E.canvasViewport.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top,wx=(mx-S.panX)/S.zoom,wy=(my-S.panY)/S.zoom,z=Math.min(1.8,Math.max(.3,S.zoom*(e.deltaY<0?1.1:.9)));S.panX=mx-wx*z;S.panY=my-wy*z;S.zoom=z;transform();};
    window.onkeydown=e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="s"){e.preventDefault();save().catch(x=>toast(x.message,"error"));}if((e.ctrlKey||e.metaKey)&&e.key==="Enter"){e.preventDefault();run();}if((e.key==="Delete"||e.key==="Backspace")&&S.selected&&!e.target.matches("input,textarea"))removeSelected();if(e.key==="Escape"){S.pending=null;render();}};
  }
  async function start(){bind();try{const h=await api("/api/health");E.versionText.textContent=`v${h.version}`;const c=await api("/api/catalog");S.catalog=c.nodes;S.specs=new Map(c.nodes.map(x=>[x.type,x]));E.catalogCount.textContent=c.count;renderCatalog();await projects();await engines();fit();setStatus("CineNode pronto. Núcleo local ativo.");}catch(e){console.error(e);setStatus(`Falha ao iniciar: ${e.message}`);toast(e.message,"error");}}
  start();
})();
