export class State {
  constructor(){this.nodes=[];this.selected=null;this.workflow=null;this.listeners=new Set()}
  subscribe(listener){this.listeners.add(listener);return()=>this.listeners.delete(listener)} emit(){for(const listener of this.listeners)listener(this)}
  setWorkflow(item){this.workflow=item;this.nodes=structuredClone(item?.definition?.nodes||[]);this.selected=null;this.emit()}
  add(type,x=120,y=120){let base=type.replace(/[^a-z0-9]/gi,"_");let id=base;let i=1;while(this.nodes.some(n=>n.id===id))id=`${base}_${i++}`;this.nodes.push({id,type,x,y,params:{},inputs:{}});this.selected=id;this.emit()}
  select(id){this.selected=id;this.emit()} remove(id){this.nodes=this.nodes.filter(n=>n.id!==id);if(this.selected===id)this.selected=null;this.emit()}
  update(id,patch){const node=this.nodes.find(n=>n.id===id);if(Object.assign(node||{},patch))this.emit()}
  definition(){return {version:1,nodes:structuredClone(this.nodes)}}
}
