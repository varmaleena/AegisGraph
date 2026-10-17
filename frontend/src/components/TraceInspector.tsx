import { Code2, Copy, Check, Route } from "lucide-react";
import { useState } from "react";
import type { Trace } from "./types";
export default function TraceInspector({trace}:{trace?:Trace}) {
 const [copied,setCopied]=useState(false);
 return <section className="trace"><div className="trace-header"><span><Code2 size={16}/> CYPHER TRACE INSPECTOR</span><div>{trace&&<span className="latency">{trace.execution_time_ms.toFixed(2)} ms</span>}<button aria-label="Copy Cypher query" disabled={!trace?.cypher_executed} onClick={async()=>{try{await navigator.clipboard.writeText(trace?.cypher_executed||"");setCopied(true);setTimeout(()=>setCopied(false),2000);}catch{setCopied(false);}}}>{copied?<Check size={14}/>:<Copy size={14}/>}</button></div></div>
 <div className="trace-meta"><span><Route size={13}/>{trace?.highlighted_node_ids.length||0} nodes highlighted</span><span>{trace?.graph||"Awaiting query"}</span></div>
 <pre className="query">{trace?.clone_command&&<span className="clone">{trace.clone_command}{"\n\n"}</span>}{trace?.cypher_executed?.trim()||"// Every agent action leaves a query trail.\n// Select an activity to inspect its evidence."}</pre>
 {trace&&<details><summary>Result rows · {trace.data.length}</summary><pre>{JSON.stringify(trace.data,null,2)}</pre></details>}
 </section>;
}