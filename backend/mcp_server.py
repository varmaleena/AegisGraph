"""Run: python -m backend.mcp_server (stdio MCP transport)."""
from mcp.server.fastmcp import FastMCP
from backend import mcp_tools as tools
from backend.db import operation

mcp = FastMCP("AegisGraph")
mcp.tool()(tools.trace_root_cause_and_blast_radius)
mcp.tool()(tools.compute_service_criticality_pagerank)
mcp.tool()(tools.resolve_bitemporal_policy)
mcp.tool()(tools.lookup_procedural_playbook)

@mcp.tool()
def ingest_and_supersede_decision(service_name: str, topic: str, person_name: str,
    new_summary: str, source: str, reason: str, timestamp: int, tenant: str="vortexpay_prod"):
    with operation(tenant):
        return tools.ingest_and_supersede_decision(service_name,topic,person_name,
            new_summary,source,reason,timestamp,tenant)

@mcp.tool()
def simulate_action_in_shadow_graph(target_service: str, action: str, tenant: str="vortexpay_prod"):
    with operation(tenant):
        return tools.simulate_action_in_shadow_graph(target_service,action,tenant)

# Register granular V2 tools as well; the isolated V2 worker exposes exactly seven.
from backend.v2_tools import TOOLS as V2_TOOLS
for tool in V2_TOOLS:
    mcp.tool()(tool)

if __name__ == "__main__":
    mcp.run()