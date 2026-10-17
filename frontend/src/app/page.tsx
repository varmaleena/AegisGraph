"use client";
import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import EvidencePanel from "@/components/EvidencePanel";
import HeaderBar from "@/components/HeaderBar";
import AgentConsole from "@/components/AgentConsole";
import TraceInspector from "@/components/TraceInspector";
import type { AgentEvent, GraphData } from "@/components/types";
const GraphCanvas=dynamic(()=>import("@/components/GraphCanvas"),{ssr:false});
const API=process.env.NEXT_PUBLIC_API_URL||"http://localhost:8000";
async function request(path:string,tenant:string,body?:object){
 const res=await fetch(API+path,{...(body?{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({tenant,...body})}:{}),cache:"no-store"});
 if(!res.ok){const err=await res.json().catch(()=>({detail:res.statusText}));throw Error(err.detail||"Request failed");}return res;
}
export default function Home(){
 const [crash,setCrash]=useState(false),[evidenceTick,setEvidenceTick]=useState(0);
 const [tenant,setTenant]=useState("vortexpay_prod"),[graph,setGraph]=useState<GraphData>({nodes:[],links:[]}),[events,setEvents]=useState<AgentEvent[]>([]),[session,setSession]=useState(""),[selected,setSelected]=useState(-1),[busy,setBusy]=useState(false),[online,setOnline]=useState(false),[error,setError]=useState(""),[view,setView]=useState("production");
 useEffect(()=>{const saved=new URLSearchParams(window.location.search).get("tenant");if(saved==="tenant_beta"||saved==="vortexpay_prod")setTenant(saved);},[]);
 const chooseTenant=(value:string)=>{setTenant(value);const url=new URL(window.location.href);url.searchParams.set("tenant",value);window.history.replaceState(null,"",url);};
 const currentGraph=useRef(""); const refreshVersion=useRef(0);
 const graphName=view==="shadow"?(tenant==="vortexpay_prod"?"vortexpay_sandbox":"tenant_beta_sandbox"):tenant;
 currentGraph.current=graphName;
 const refresh=useCallback(async()=>{
  const version=++refreshVersion.current;
  try {
   const data=await (await request("/graph?tenant="+graphName,tenant)).json();
   if(currentGraph.current===graphName&&version===refreshVersion.current){setGraph(data);setOnline(true);}
  } catch(e) {if(currentGraph.current===graphName)setOnline(false);throw e;}
 },[graphName,tenant]);
 useEffect(()=>{let live=true;setSession("");setGraph({nodes:[],links:[]});setEvents([]);setSelected(-1);setError("");setView("production");
  request("/session?tenant="+tenant,tenant).then(r=>r.json()).then(d=>{if(live){setSession(d.session_id);setEvents(d.events);setSelected(d.events.findLastIndex((e:AgentEvent)=>Boolean(e.trace.cypher_executed)));}}).catch(e=>{if(live){setError(e.message);setOnline(false);}});
  return()=>{live=false;};},[tenant]);
 useEffect(()=>{refresh().catch(e=>{setError(e.message);setOnline(false);});},[refresh]);
 const add=useCallback((e:AgentEvent)=>{setEvents(prev=>{if(e.trace.cypher_executed)setSelected(prev.length);return [...prev,e];});},[]);
 const reset=async()=>{const d=await(await request("/reset-session",tenant,{})).json();setSession(d.session_id);setEvents([]);setSelected(-1);};
 const run=async(action:string,message?:string)=>{
  if(busy)return;setBusy(true);setError("");
  try{
   if(action==="reset"){await reset();return;}
   if(action==="policy"||action==="simulate"){
    const path=action==="policy"?"/ingest-contradiction":"/simulate";
    add(await(await request(path,tenant,action==="simulate"?{action:"isolate"}:{})).json());
   } else if(action==="security"){
    await request("/api/security-policy?tenant="+tenant,tenant,{});
   } else if(action==="cancel"){
    await request("/api/runs/"+message+"/cancel?tenant="+tenant,tenant,{});
   } else {
    if(action==="replay")await reset();
    const response=await request(action==="resume"?"/api/runs/"+message+"/resume?tenant="+tenant:"/api/runs",tenant,
      action==="resume"?{}:{message:message||"Investigate ERR_AUTH_POOL_EXHAUSTED in checkout-api",interrupt_at_step:crash?3:null});
    const reader=response.body!.getReader(),decoder=new TextDecoder();let buffer="";
    for(;;){const {done,value}=await reader.read();buffer+=decoder.decode(value,{stream:!done});
     let split;while((split=buffer.indexOf("\n\n"))>=0){
      const packet=buffer.slice(0,split);buffer=buffer.slice(split+2);
      const kind=packet.match(/event: (.+)/)?.[1];const raw=packet.split("\n").filter(l=>l.startsWith("data: ")).map(l=>l.slice(6)).join("\n");
      if(raw){const data=JSON.parse(raw);if(["step","done","CRASH_SIMULATED"].includes(kind||"")&&data.summary){add(data);await refresh();setEvidenceTick(v=>v+1);}if(kind==="session")setSession(data.session_id);if(kind==="error")throw Error(data.summary||data.detail||"Run interrupted");}
     }if(done)break;
    }
   }
   await refresh();
  }catch(e){setError(e instanceof Error?e.message:"Request failed");}
  finally{setBusy(false);setEvidenceTick(v=>v+1);}
 };
 const trace=events[selected]?.trace;
 const stableGraph=useMemo(()=>graph,[graph]);
 return <main><HeaderBar tenant={tenant} setTenant={chooseTenant} reset={()=>void run("reset")} busy={busy} online={online}/>
 <div className="workspace"><AgentConsole events={events} busy={busy} run={(a,m)=>void run(a,m)} select={setSelected} selected={selected} session={session}/>
 <div className="right-panel"><div className="view-tabs"><div><button className={view==="production"?"active":""} onClick={()=>setView("production")}>Company brain</button><button className={view==="shadow"?"active":""} onClick={()=>setView("shadow")}>Shadow sandbox</button></div><span><i/> LIVE GRAPH</span></div>
 <GraphCanvas data={stableGraph} highlighted={trace?.highlighted_node_ids||[]} graph={graphName}/>
 <TraceInspector trace={trace}/><EvidencePanel tenant={tenant} tick={evidenceTick} busy={busy} crash={crash} setCrash={setCrash} onAction={(a,id)=>void run(a,id)}/></div></div>
 {error&&<div role="alert" className="error"><strong>Operation unavailable</strong><span>{error}</span><button onClick={()=>{setError("");void refresh().catch(e=>setError(e.message));}}>Retry connection</button><button aria-label="Dismiss error" onClick={()=>setError("")}>×</button></div>}
 <footer className="statusbar"><span><i/> AEGISGRAPH / VORTEXPAY LAB</span><span>CONNECTED ACTION <b>·</b> AGENT MEMORY <b>·</b> COMPANY BRAIN</span><span>POWERED BY FALKORDB ↗</span></footer></main>;
}