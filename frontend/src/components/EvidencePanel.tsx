"use client";
import {useEffect,useState} from "react";
type Run={provider?:string;model?:string;run_id:string;execution_mode:string;status:string;current_step:number;llm_calls:number;mcp_tool_calls:number;total_tokens:number;falkordb_compute_ms:number;wall_clock_ms:number;pre_incident_error_rate:number;post_incident_error_rate:number;precondition_verdict:string;rejection_reason:string;playbook:string;measurement_source?:string;last_error?:string};
type Service={name:string;error_rate:number;p99_latency_ms:number;status:string};
const API=process.env.NEXT_PUBLIC_API_URL||"http://localhost:8000";
export default function EvidencePanel({tenant,sandbox,tick,busy,crash,setCrash,onAction}:{tenant:string;sandbox:boolean;tick:number;busy:boolean;crash:boolean;setCrash:(v:boolean)=>void;onAction:(action:string,id?:string)=>void}){
 const [runs,setRuns]=useState<Run[]>([]),[services,setServices]=useState<Service[]>([]);
 const [model,setModel]=useState<{provider:string;model:string;configured:boolean;key_name:string}|null>(null);
 const [gate,setGate]=useState<{verdict:string;reason:string}|null>(null);
 const [error,setError]=useState("");
 useEffect(()=>{let live=true;fetch(API+"/api/evidence?tenant="+tenant+"&sandbox="+sandbox,{cache:"no-store"}).then(async r=>{if(!r.ok)throw Error("Evidence unavailable");return r.json();}).then(d=>{if(live){setRuns(d.runs);setServices(d.services);setModel(d.model);setGate(d.gate);setError("");}}).catch(e=>{if(live)setError(e.message)});return()=>{live=false}},[tenant,sandbox,tick,busy]);
 const interrupted=runs.findLast(r=>["INTERRUPTED_CRASH","INTERRUPTED_ERROR"].includes(r.status));
 return <details className="evidence" open><summary>EMPIRICAL TELEMETRY & REPLAY BENCHMARK</summary>
 <div className="v2-controls"><label><input type="checkbox" checked={crash} disabled={busy} onChange={e=>setCrash(e.target.checked)}/> Simulate crash at step 3</label>
 <button disabled={busy} onClick={()=>onAction("security")}>Inject security directive · DEC-03</button>
 {interrupted&&<><button disabled={busy} onClick={()=>onAction("resume",interrupted.run_id)}>Resume from FalkorDB</button><button disabled={busy} onClick={()=>onAction("cancel",interrupted.run_id)}>Cancel interrupted run</button></>}</div>
 {model&&<p className={model.configured?"model-ready":"model-missing"}>{model.configured?(runs.some(r=>r.measurement_source==="LIVE_PROVIDER"&&r.status==="COMPLETED"&&r.provider===model.provider&&r.model===model.model)?"MODEL CONFIGURED · LIVE RUN VERIFIED":"MODEL CONFIGURED · LIVE VALIDATION REQUIRED"):"API KEY REQUIRED"} · {model.provider} / {model.model}{!model.configured&&" · Add "+model.key_name+" to local .env and recreate backend"}</p>}
 {error&&<p role="alert">{error}</p>}
 {gate&&<p title={gate.reason}>LIVE PLAYBOOK GATE - {gate.verdict}{gate.reason&&" - "+gate.reason}</p>}
 <p>{sandbox?"SHADOW SANDBOX TELEMETRY":"PRODUCTION SIMULATOR TELEMETRY"}</p>
 <div className="metric-bars">{services.filter(s=>["checkout-api","payment-orchestrator","token-auth-service"].includes(s.name)).map(s=><div key={s.name}><strong>{s.name}</strong><span style={{color:s.error_rate<.01?"#8ce2bf":"#ee7d91"}}>{(s.error_rate*100).toFixed(2)}% error · {s.p99_latency_ms?.toFixed(1)} ms p99</span><progress max={1} value={s.error_rate}/></div>)}</div>
 <div className="benchmark-scroll"><table><thead><tr>{["Run / mode","Gate / status","LLM","MCP","Tokens","DB ms","Duration ms","Error before → after","Playbook"].map(h=><th key={h}>{h}</th>)}</tr></thead><tbody>{runs.map((r,i)=><tr key={r.run_id} title={r.rejection_reason||r.last_error||r.run_id}><td>#{i+1} {r.execution_mode}<small>{r.measurement_source==="TEST_FIXTURE"?"TEST FIXTURE · NOT A LIVE MODEL":r.run_id.slice(0,12)}</small></td><td>{r.precondition_verdict}<small>{r.status} · step {r.current_step}</small>{r.rejection_reason&&<em>{r.rejection_reason}</em>}</td><td>{r.llm_calls}</td><td>{r.mcp_tool_calls}</td><td>{r.total_tokens}</td><td>{r.falkordb_compute_ms.toFixed(2)}</td><td>{r.wall_clock_ms}</td><td>{(100*r.pre_incident_error_rate).toFixed(2)}% → {(100*r.post_incident_error_rate).toFixed(2)}%</td><td>{r.playbook?.slice(-12)||"—"}</td></tr>)}</tbody></table>{!runs.length&&<p>No runs yet. Metrics populate from persisted InvestigationRun nodes.</p>}</div>
 <small>Deterministic simulator telemetry, not real infrastructure. Tokens come from provider usage. Warm replay uses zero LLM calls. Duration includes active execution segments; resume downtime is excluded.</small>
 </details>;
}