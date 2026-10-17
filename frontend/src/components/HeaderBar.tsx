import { Shield, Database, RotateCcw, ArrowUpRight } from "lucide-react";
export default function HeaderBar({tenant,setTenant,reset,busy,online}:{tenant:string;setTenant:(v:string)=>void;reset:()=>void;busy:boolean;online:boolean}) {
 return <header className="topbar">
  <a className="brand" href="/"><span className="brand-icon"><Shield size={24}/></span><span>Aegis<span className="muted">Graph</span><small>ORGANIZATIONAL INTELLIGENCE</small></span></a>
  <div className="header-controls"><span className={"connection "+(online?"online":"")}><i/>{online?"FalkorDB connected":"Connecting to FalkorDB"}</span>
   <label className="tenant"><Database size={14}/><select aria-label="Active tenant" disabled={busy} value={tenant} onChange={e=>setTenant(e.target.value)}><option value="vortexpay_prod">VortexPay / Production</option><option value="tenant_beta">Beta / Isolated tenant</option></select></label>
   <button className="icon-button" aria-label="Start new session" onClick={reset} disabled={busy}><RotateCcw size={16}/></button>
   <a className="docs-link" href={(process.env.NEXT_PUBLIC_API_URL||"http://localhost:8000")+"/docs"} target="_blank" rel="noreferrer">API docs <ArrowUpRight size={14}/></a>
  </div>
 </header>;
}