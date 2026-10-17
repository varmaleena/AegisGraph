export type Trace = {data:Record<string,unknown>[];cypher_executed:string;execution_time_ms:number;highlighted_node_ids:string[];graph:string;clone_command?:string};
export type AgentEvent = {agent:string;summary:string;trace:Trace};
export type GraphNode = {id:string;label:string;properties:Record<string,unknown>;x?:number;y?:number};
export type GraphLink = {source:string|GraphNode;target:string|GraphNode;type:string};
export type GraphData = {nodes:GraphNode[];links:GraphLink[]};