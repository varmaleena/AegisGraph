import { motion } from "framer-motion";
import { ArrowUpRight, BookOpen, GitBranch, Terminal, Zap, Send, LoaderCircle } from "lucide-react";
import type { AgentEvent } from "./types";
import { useEffect, useRef, useState } from "react";
const colors:Record<string,string>={Scribe:"#f3bc64",Navigator:"#92a7ff",Commander:"#67d9ad",System:"#91a0b5",User:"#e4eaf3"};
export default function AgentConsole({events,busy,run,select,selected,session}:{events:AgentEvent[];busy:boolean;run:(action:string,message?:string)=>void;select:(i:number)=>void;selected:number;session:string}) {
 const [message,setMessage]=useState(""); const end=useRef<HTMLDivElement>(null);
 useEffect(()=>{end.current?.scrollIntoView({behavior:"smooth",block:"nearest"});},[events]);
 const actions=[["policy","01","Inject policy contradiction",BookOpen],["incident","02","Investigate checkout incident",GitBranch],["replay","03","New session · replay memory",Zap],["simulate","04","Simulate service isolation",Terminal]] as const;
 return <section className="console">
  <div className="section-top"><span className="eyebrow">OPERATIONS WORKSPACE</span><span className="pill">SYNTHETIC DATA</span></div>
  <h1>Context becomes<br/><span className="headline-accent">a course of action.</span></h1>
  <p className="intro">One company brain. Three specialist agents.<br/>Every decision has a path you can inspect.</p>
  <div className="agent-roster">{["Scribe","Navigator","Commander"].map((name,i)=><div key={name}><span className="agent-avatar" style={{color:colors[name],background:colors[name]+"16"}}>{name[0]}</span><span>{name}<small>{["Knowledge","Connected action","Procedural memory"][i]}</small></span><i className={busy?"working":""}/></div>)}</div>
  <div className="demo-title"><span className="eyebrow">RUN THE VORTEXPAY SCENARIO</span><span>4 steps</span></div>
  <div className="actions">{actions.map(([action,n,title,Icon])=><button key={action} disabled={busy} onClick={()=>run(action)}><span className="action-number">{n}</span><Icon size={16}/><span>{title}</span><ArrowUpRight size={15}/></button>)}</div>
  <div className="activity-title"><span><i className={busy?"live-dot":""}/> AGENT ACTIVITY</span><small>{session?session.slice(0,12):"No session"}</small></div>
  <div className="activity" role="log" aria-live="polite">
   {!events.length&&<div className="empty-activity"><Terminal size={22}/><p>Your investigation starts here.</p><small>Configure the model key, then trigger an incident.<br/>Agent handoffs and evidence will appear below.</small></div>}
   {events.map((e,i)=><motion.button initial={{opacity:0,y:8}} animate={{opacity:1,y:0}} key={i} className={"event "+(selected===i?"selected":"")} onClick={()=>select(i)}><span className="event-avatar" style={{color:colors[e.agent]||colors.System}}>{e.agent[0]}</span><span><strong style={{color:colors[e.agent]}}>{e.agent}<small>{e.trace.cypher_executed?e.trace.execution_time_ms.toFixed(2)+" ms":"EVENT"}</small></strong><p>{e.summary}</p>{e.trace.cypher_executed&&<em>Inspect graph evidence ↗</em>}</span></motion.button>)}
   {busy&&<div className="processing"><LoaderCircle size={14} className="spin"/> Traversing graph context…</div>}<div ref={end}/>
  </div>
  <form className="composer" onSubmit={e=>{e.preventDefault();run("incident",message);setMessage("");}}><input aria-label="Incident description" placeholder="Describe the checkout incident for the model…" value={message} onChange={e=>setMessage(e.target.value)} disabled={busy}/><button aria-label="Run investigation" disabled={busy}><Send size={16}/></button></form>
  <div className="console-footer"><span>FALKORDB IS THE SOURCE OF TRUTH</span><span>NO SECONDARY DATABASE</span></div>
 </section>;
}