"use client";
import ForceGraph2D from "react-force-graph-2d";
import { useEffect, useMemo, useRef, useState } from "react";
import { Crosshair, ZoomIn, ZoomOut, Network } from "lucide-react";
import type { GraphData, GraphNode } from "./types";
export const palette:Record<string,string>={Service:"#6b9afc",Decision:"#f3bc64",PR:"#b49afb",Playbook:"#67d9ad",ActionStep:"#67d9ad",SymptomSignature:"#67d9ad",Incident:"#ee7d91",Person:"#a5b5ca",Team:"#8295ad",Document:"#a5b5ca",Hypothesis:"#b49afb",Session:"#70819b",Task:"#8498b2",Runtime:"#52617b",Event:"#52617b"};
export default function GraphCanvas({data,highlighted,graph}:{data:GraphData;highlighted:string[];graph:string}) {
 const wrap=useRef<HTMLDivElement>(null);
 const api=useRef<import("react-force-graph-2d").ForceGraphMethods<GraphNode>|undefined>(undefined);
 const [size,setSize]=useState({width:650,height:450}); const [focus,setFocus]=useState<GraphNode|null>(null);
 const active=new Set(highlighted);
 useEffect(()=>{if(!wrap.current)return;const obs=new ResizeObserver(([e])=>setSize({width:e.contentRect.width,height:e.contentRect.height}));obs.observe(wrap.current);return()=>obs.disconnect();},[]);
 const visible=useMemo(()=>{
  const nodes=data.nodes.filter(n=>!["Event","Runtime"].includes(n.label)).map(n=>({...n}));
  const ids=new Set(nodes.map(n=>n.id));
  const id=(v:string|GraphNode)=>typeof v==="string"?v:v.id;
  return {nodes,links:data.links.filter(l=>ids.has(id(l.source))&&ids.has(id(l.target))).map(l=>({...l}))};
 },[data]);
 useEffect(()=>{api.current?.d3Force("charge")?.strength(-180);api.current?.d3Force("link")?.distance(65);
 const timer=setTimeout(()=>api.current?.zoomToFit(400,55),1200);return()=>clearTimeout(timer);},[data]);
 useEffect(()=>{setFocus(null);},[graph]);
 // ForceGraph mutates link endpoints; memoized data is provided by the parent.
 return <div className="graph-view">
  <div className="graph-title"><span><Network size={16}/> LIVE KNOWLEDGE GRAPH</span><span className="graph-counter">{visible.nodes.length} nodes <b>·</b> {visible.links.length} relationships</span></div>
  <div className="graph-surface" ref={wrap}>
   <ForceGraph2D ref={api} width={size.width} height={size.height} graphData={visible} backgroundColor="rgba(0,0,0,0)" nodeId="id" nodeLabel={n=>String(n.properties.name||n.properties.title||n.id)} linkColor={()=>"#27384d"} linkWidth={1} linkDirectionalArrowLength={3} linkDirectionalArrowRelPos={0.9} cooldownTicks={100} onEngineStop={()=>api.current?.zoomToFit(400,55)} d3VelocityDecay={0.3} onNodeClick={n=>setFocus(n)}
    nodeCanvasObject={(node,ctx,scale)=>{
      const x=node.x||0,y=node.y||0,c=palette[node.label]||"#91a0b5", lit=active.has(node.id);
      const r=node.label==="Service"?6:4;
      if(lit){ctx.beginPath();ctx.arc(x,y,r+6+Math.sin(Date.now()/250)*2,0,2*Math.PI);ctx.fillStyle=c+"18";ctx.fill();ctx.strokeStyle=c+"66";ctx.lineWidth=1/scale;ctx.stroke();}
      ctx.beginPath();ctx.arc(x,y,r,0,2*Math.PI);ctx.fillStyle=c;ctx.shadowColor=lit?c:"transparent";ctx.shadowBlur=lit?15:0;ctx.fill();ctx.shadowBlur=0;
      const text=String(node.properties.name||node.properties.title||
        (node.label==="Hypothesis"?node.properties.agent+" hypothesis":
         node.label==="Task"?node.properties.agent+" task":
         node.label==="Session"?"Session":node.id));
      ctx.font=`${Math.max(9/scale,2)}px ui-monospace, monospace`;ctx.textAlign="center";ctx.fillStyle=lit?"#f2f6ff":"#94a6c1";ctx.fillText(text.length>28?text.slice(0,26)+"…":text,x,y+r+12/scale);
    }}/>
   {!visible.nodes.length&&<div className="graph-empty"><Network size={34}/><p>Waiting for graph context</p><small>Start FalkorDB and seed the VortexPay graph.</small></div>}
   <div className="graph-label"><i/> {graph}<small>GRAPH-NATIVE CONTEXT</small></div>
   <div className="graph-controls"><button aria-label="Zoom in" onClick={()=>api.current?.zoom((api.current.zoom()||1)*1.25,300)}><ZoomIn size={17}/></button><button aria-label="Zoom out" onClick={()=>api.current?.zoom((api.current.zoom()||1)/1.25,300)}><ZoomOut size={17}/></button><button aria-label="Fit graph" onClick={()=>api.current?.zoomToFit(400,50)}><Crosshair size={17}/></button></div>
   {focus&&<div className="node-detail"><button aria-label="Close node details" onClick={()=>setFocus(null)}>×</button><span style={{color:palette[focus.label]}}>{focus.label}</span><strong>{focus.id}</strong><pre>{JSON.stringify(focus.properties,null,2)}</pre></div>}
  </div>
  <div className="legend">{["Service","Decision","PR","Playbook","Incident","Person"].map(l=><span key={l}><i style={{background:palette[l]}}/>{l==="PR"?"Pull request":l}</span>)}<small>Click a node to inspect</small></div>
 </div>;
}