Save this document as MASTER_SPEC_V2.md in the root of your repository and instruct Codex / Antigravity to execute it as an incremental upgrade over your existing v1 codebase.
Because you already have the v1 foundation running, this specification is structured as a Drop-In Engineering Upgrade that replaces scripted orchestration and mock state flips with true model-directed MCP reasoning, a deterministic graph-physics telemetry simulator, precondition-checked versioned playbooks, empirical run benchmarks, and crash-resilient FalkorDB task checkpointing.
MASTER ENGINEERING SPECIFICATION v2.0: AegisGraph
Upgrade Focus: True Autonomy, Precondition-Verified Procedural Memory, Graph Physics Simulation & Durable Graph Checkpointing
1. Architectural Delta (v1 \rightarrow v2)
| Component | v1 Implementation (Already Built) | v2 Production Upgrade (To Implement Now) |
|---|---|---|
| Agent Loop | Fixed sequential function calls (Tool A -> Tool B -> Tool C). | Priority 1: Model-Directed ReAct Loop over MCP. The LLM inspects graph frontier hints and dynamically chooses which tool to call next. |
| Playbook Replay | Blindly executes if error_code matches. | Priority 2: Precondition-Gated Versioned Playbooks. Checks if governing (:Decision) is still ACTIVE and if upstream [:DEPENDS_ON] topology hash matches. Rejects stale playbooks and compiles v2. |
| Service Remediation | Sets node.status = 'HEALTHY' directly. | Priority 3: Deterministic Graph Physics Simulator. Mutates real config parameters (timeout_ms, max_pool_size, circuit_breaker), recalculates cascading latency/error math across edges, and verifies recovery. |
| Playbook Creation | Saves a static template after an incident. | Priority 4: Verified Trace Compiler. Extracts only the exact mutation tool call(s) that caused a verified metric drop (error_rate < 0.01), recording exact arguments and postconditions. |
| Judge Proof UI | Single-run trace viewer. | Priority 5: Empirical Run Comparison Panel. Benchmarks Cold Discovery vs. Warm Replay vs. Rejected Stale Replay across LLM calls, tokens, FalkorDB ms, and duration. |
| Runtime State | In-memory Python variables during a run. | Priority 6: Durable FalkorDB Task Checkpointing. Every step persists to (:InvestigationRun)-[:STEP_TRACE]->(:ToolTrace). Backend can abort at Step 3 and resume seamlessly from FalkorDB. |
2. Extended FalkorDB Schema (v2 Additions)
Add these properties and node labels to backend/seed_graph.py so the graph supports physics simulation, precondition hashing, and crash recovery.
2.1 Upgraded (:Service) Physics Properties (Priority 3)
Every :Service node must be seeded with physical configuration and telemetry attributes:
(:Service {
  id: STRING,
  name: STRING,
  tier: INT,
  // Physical Config Parameters (Mutable by Agent Tools)
  timeout_ms: INT,            // e.g., checkout-api=2000, token-auth-service=150 (faulty!)
  max_pool_size: INT,         // e.g., token-auth-service=20 (faulty under load!), redis=500
  circuit_breaker: BOOLEAN,   // e.g., false
  base_processing_ms: INT,    // Intrinsic latency of the service
  // Computed Telemetry (Calculated by Simulator, NEVER set manually to 'HEALTHY')
  current_load_rps: INT,      // e.g., 1200
  p99_latency_ms: FLOAT,      // Computed bottom-up across [:DEPENDS_ON]
  error_rate: FLOAT,          // Computed 0.0 to 1.0
  status: STRING              // Derived: 'HEALTHY' (<1% err), 'DEGRADED' (1-15%), 'CRITICAL' (>15%)
})

2.2 Versioned Playbooks & Preconditions Schema (Priorities 2 & 4)
(:SymptomSignature {id: STRING, error_code: STRING, entry_service: STRING})
  -[:HAS_PLAYBOOK]->(:Playbook {
      id: STRING,                   // e.g., "PB-AUTH-01-v1"
      version: INT,                 // 1, 2, ...
      status: STRING,               // 'ACTIVE' | 'SUPERSEDED'
      required_decision_id: STRING, // e.g., "DEC-02" (Must be status='ACTIVE' to replay!)
      topology_hash: STRING,        // Deterministic string of sorted upstream dependency names
      required_config_bounds: STRING, // JSON e.g., '{"max_allowed_timeout_ms": 500}'
      postcondition_expr: STRING,   // e.g., "error_rate < 0.01 AND p99_latency_ms < 500"
      created_at: INT,
      verified_runs: INT
  })
  -[:SUPERSEDES_PLAYBOOK {reason: STRING, timestamp: INT}]->(:Playbook)

(:Playbook)-[:HAS_STEP {order: INT}]->(:ActionStep {
    id: STRING,
    mcp_tool: STRING,               // e.g., "apply_service_config_mutation"
    tool_args_json: STRING,         // Exact verified JSON args from discovery run
    evidence_node_id: STRING,       // e.g., "PR-409" or "DEC-02"
    pre_error_rate: FLOAT,          // e.g., 0.68
    post_error_rate: FLOAT          // e.g., 0.002
})

2.3 Durable Investigation Checkpoint Schema (Priorities 5 & 6)
(:InvestigationRun {
    run_id: STRING,                 // e.g., "RUN-1001"
    incident_id: STRING,
    entry_service: STRING,
    error_code: STRING,
    execution_mode: STRING,         // 'DISCOVERY' | 'WARM_REPLAY' | 'REJECTED_REPLAY_REINVESTIGATION'
    status: STRING,                 // 'IN_PROGRESS' | 'INTERRUPTED_CRASH' | 'COMPLETED'
    current_step: INT,
    llm_calls: INT,
    mcp_tool_calls: INT,
    total_tokens: INT,
    falkordb_compute_ms: FLOAT,
    wall_clock_ms: INT,
    pre_incident_error_rate: FLOAT,
    post_incident_error_rate: FLOAT,
    playbook_used_or_created: STRING,
    rejection_reason: STRING,       // Populated if Playbook v1 was rejected
    messages_checkpoint_json: STRING // Serialized LLM tool-calling conversation history
})-[:EXECUTED_STEP {step_num: INT}]->(:ToolTrace {
    trace_id: STRING,
    agent_role: STRING,             // 'Navigator' | 'Scribe' | 'Commander'
    tool_name: STRING,
    tool_args_json: STRING,
    cypher_executed: STRING,
    falkordb_latency_ms: FLOAT,
    result_summary: STRING,
    highlighted_nodes_json: STRING
})

3. Detailed Specification for the 6 Core Modules
Module 1: The Measurable Service Physics Simulator (backend/simulator.py) — Priority 3
Never allow an agent tool to set s.status = 'HEALTHY'. Instead, implement recalculate_graph_telemetry(graph_name="vortexpay_prod") which runs after every configuration change or chaos injection.
How the Physics Math Works
 * Fetch all (:Service) nodes and [:DEPENDS_ON] edges from FalkorDB in a single Cypher query.
 * Sort services in reverse topological order (leaf dependencies like redis-session-cluster and ledger-db-proxy first; root callers like web-storefront last).
 * For each service S, compute its metrics deterministically from its physical config and its children C_i:
   * Pool Starvation Check: If S.\text{current\_load\_rps} / S.\text{max\_pool\_size} > 25 and S.\text{circuit\_breaker} == \text{false}, then S suffers connection pool queueing:
     
   * Effective Latency:
     
   * Timeout Misconfiguration Check: For each dependency C_i, if S.\text{timeout\_ms} < C_i.\text{p99\_latency\_ms}:
     * If S.\text{circuit\_breaker} == \text{false}, S suffers cascading timeout failures (timeout_error = min(0.95, (C_i.p99_latency_ms - S.timeout_ms) / C_i.p99_latency_ms + 0.35)).
     * If S.\text{circuit\_breaker} == \text{true} and S.\text{max\_pool\_size} \ge 80, fallback pooling absorbs the spike (timeout_error = 0.004).
   * Cascading Error Propagation:
     
   * Derived Status:
     * error_rate < 0.01 \rightarrow 'HEALTHY'
     * 0.01 <= error_rate < 0.15 \rightarrow 'DEGRADED'
     * error_rate >= 0.15 \rightarrow 'CRITICAL'
 * Write the updated p99_latency_ms, error_rate, and status back to FalkorDB in one batch UNWIND Cypher query.
Why This Makes the Demo Undeniable
 * Seeded Fault State: token-auth-service has timeout_ms = 150, max_pool_size = 20, circuit_breaker = false while redis-session-cluster spikes to 190ms. This causes token-auth-service to hit 68% error_rate, cascading to checkout-api at 58% error_rate (CRITICAL).
 * Policy Constraint (DEC-02): Sarah Chen’s active Slack decision states: "Under no circumstances raise token-auth-service timeout above 300ms; instead increase max_pool_size >= 100 and set circuit_breaker = true."
 * If an agent tries a naive fix or violates policy, the simulator math proves whether the system actually recovered.
Module 2: Model-Directed MCP Tool Suite (backend/mcp_server.py) — Priority 1
Replace any hardcoded Python sequence with an LLM Tool-Calling Loop (using OpenAI gpt-4o / gpt-4.1 or Anthropic tool use) that has access to these 7 granular MCP tools. Each tool returns Graph Frontier Hints (unexplored_edges) so the model decides its own investigation path:
 * inspect_service_telemetry_and_frontier(service_name: str)
   * Cypher: Returns the service's current telemetry (error_rate, p99_latency_ms, timeout_ms, max_pool_size, circuit_breaker) PLUS counts of attached edges (upstream_dependencies_count, recent_prs_count, governing_decisions_count).
   * Purpose: Lets the model observe a node and decide whether to hop to dependencies, PRs, or policies.
 * traverse_dependency_SingleOrMultiHop(service_name: str, max_hops: int = 3)
   * Cypher: Runs MATCH p = (s:Service {name: $service_name})-[:DEPENDS_ON*1..3]->(dep:Service) and returns telemetry along every hop so the model spots where error_rate originates.
 * inspect_recent_prs_and_authors(service_name: str)
   * Cypher: Finds (:PR)-[:MODIFIED]->(:Service {name: $service_name}) and (:Person)-[:AUTHORED]->(:PR), returning the exact config diff introduced by PR-409.
 * query_bitemporal_policies(service_name: str)
   * Cypher: Queries active and :SUPERSEDES (:Decision) nodes governing the service so the agent learns architectural constraints before acting.
 * compute_blast_radius_pagerank()
   * Cypher: CALL algo.pageRank('Service', 'DEPENDS_ON') to prioritize Tier-1 critical path nodes.
 * simulate_config_mutation_in_sandbox(service_name: str, timeout_ms: int, max_pool_size: int, circuit_breaker: bool)
   * Action: Clones vortexpay_prod services into vortexpay_sandbox, applies the proposed config change, runs recalculate_graph_telemetry("vortexpay_sandbox"), and returns the simulated before/after error_rate of checkout-api and token-auth-service without touching production.
 * apply_verified_mutation_to_prod(service_name: str, timeout_ms: int, max_pool_size: int, circuit_breaker: bool, justifying_decision_id: str, justifying_pr_id: str)
   * Action: Applies the change to vortexpay_prod, runs recalculate_graph_telemetry("vortexpay_prod"), verifies error_rate < 0.01, and returns the measured telemetry improvement.
Module 3: Versioned Playbooks with Precondition Gate (backend/playbook_engine.py) — Priorities 2 & 4
A. Precondition Evaluation (Before Investigation Starts)
When an incident triggers on (entry_service, error_code), Commander runs this exact Precondition Gate Cypher query against FalkorDB:
MATCH (sig:SymptomSignature {error_code: $error_code, entry_service: $entry_service})-[:HAS_PLAYBOOK]->(pb:Playbook {status: 'ACTIVE'})
OPTIONAL MATCH (dec:Decision {id: pb.required_decision_id})
OPTIONAL MATCH (s:Service {name: $entry_service})-[:DEPENDS_ON*1..4]->(dep:Service)
WITH pb, dec, collect(DISTINCT dep.name) AS raw_deps
RETURN 
  pb.id AS playbook_id,
  pb.version AS version,
  pb.required_decision_id AS required_decision_id,
  dec.status AS decision_status,
  pb.topology_hash AS expected_topology_hash,
  raw_deps AS live_dependencies

In Python (playbook_engine.py), evaluate the 3 preconditions:
 * Policy Precondition: Is decision_status == 'ACTIVE'? If dec.status == 'SUPERSEDED' (because a new Slack policy or security directive superseded DEC-02 with DEC-03), return:
   * verdict = "REJECTED_STALE_POLICY"
   * reason = f"Playbook {pb.id} relies on Decision {pb.required_decision_id}, which was SUPERSEDED in the Company Brain."
 * Topology Precondition: Compute live_hash = "|".join(sorted(live_dependencies)). If live_hash != pb.topology_hash, return:
   * verdict = "REJECTED_TOPOLOGY_DRIFT"
   * reason = f"Dependency topology changed from [{pb.topology_hash}] to [{live_hash}]."
 * Valid Replay: If both pass, execute the saved (:ActionStep) nodes directly against vortexpay_prod, verify the postcondition (checkout-api.error_rate < 0.01), and complete the run in 1 LLM call and <2 seconds.
B. Compiling the Actual Verified Action Sequence (Priority 4)
When the agent runs in DISCOVERY or REJECTED_REPLAY_REINVESTIGATION mode:
 * Track every tool call in (:ToolTrace).
 * Only when apply_verified_mutation_to_prod succeeds and recalculate_graph_telemetry confirms checkout-api.error_rate < 0.01, trigger compile_verified_playbook().
 * Extract:
   * The exact tool_args_json passed to apply_verified_mutation_to_prod
   * The justifying_decision_id (DEC-02 or DEC-03) discovered during the investigation
   * The current topology_hash
   * The measured pre_error_rate and post_error_rate
 * If an older (:Playbook) existed for this (:SymptomSignature), set old_pb.status = 'SUPERSEDED' and create (new_pb:Playbook {version: old_pb.version + 1, status: 'ACTIVE'})-[:SUPERSEDES_PLAYBOOK {reason: $rejection_reason, timestamp: $now}]->(old_pb).
Module 4: Durable Task Checkpointing & Crash Recovery (backend/orchestrator.py) — Priority 6
To prove FalkorDB is the durable state engine (Rule 3):
 * Step-Level Graph Checkpointing:
   Inside the model-directed ReAct loop (while step < max_steps:), after every single tool execution:
   * Serialize the current OpenAI/LLM messages array into (:InvestigationRun {run_id}).messages_checkpoint_json.
   * Increment current_step, llm_calls, mcp_tool_calls, total_tokens, and falkordb_compute_ms on the (:InvestigationRun) node in FalkorDB.
   * Create the linked (:ToolTrace) node in FalkorDB.
 * Simulated Backend Crash Mode (interrupt_at_step: Optional[int]):
   * Add a toggle in the UI: "Simulate Crash at Step 3".
   * When enabled, as soon as current_step == 3 finishes writing its checkpoint to FalkorDB, the backend sets run.status = 'INTERRUPTED_CRASH', wipes all local Python variables, and closes the HTTP stream with a CRASH_SIMULATED event.
 * Graph-Backed Resume Endpoint (POST /api/runs/{run_id}/resume):
   * Queries FalkorDB:
     MATCH (r:InvestigationRun {run_id: $run_id})
OPTIONAL MATCH (r)-[:EXECUTED_STEP]->(t:ToolTrace)
RETURN r, collect(t) AS completed_traces

   * Rehydrates the exact messages list from r.messages_checkpoint_json stored inside FalkorDB, sets r.status = 'IN_PROGRESS', and continues the LLM tool-calling loop from Step 4 to completion.
4. The Frontend Upgrade: Evidence & Comparison Panel (frontend/src/components/EvidencePanel.tsx) — Priority 5
Add a collapsible bottom dock or right-hand tab in your Next.js UI called "Empirical Telemetry & Replay Benchmark". It fetches MATCH (r:InvestigationRun) RETURN r ORDER BY r.run_id ASC from FalkorDB and renders:
 * Live Service Telemetry Gauges:
   * Shows real-time error_rate (%) and p99_latency_ms (ms) bars for checkout-api, payment-orchestrator, and token-auth-service changing dynamically from Red (58.4% err / 1420ms) to Emerald (0.2% err / 95ms) when the physics simulator runs.
 * The 3-Mode Benchmark Table:
   * Automatically populates as you run the demo scenarios:
     * Row 1: Run #1 (DISCOVERY) — Shows 5–6 MCP tool calls chosen by the model, ~4,200 tokens, ~12s duration, Playbook v1 Compiled, Error Rate: 58.4% -> 0.2%.
     * Row 2: Run #2 (WARM_REPLAY) — Shows Precondition Check (DEC-02 = ACTIVE, Topology Hash = MATCH), 1 MCP tool call, ~550 tokens (87% reduction), ~1.4s duration, Playbook v1 Executed.
     * Row 3: Run #3 (REJECTED_REPLAY_REINVESTIGATION) — Triggered after clicking "Inject New Security Policy (DEC-03 Supersedes DEC-02)". Shows red badge: Playbook v1 Rejected: Governing Decision DEC-02 is SUPERSEDED, followed by dynamic model reinvestigation and Playbook v2 Compiled (:SUPERSEDES_PLAYBOOK -> v1).
5. Master Implementation Prompt for Codex / Antigravity
Copy and paste the block below directly into Codex / Antigravity / Cursor to upgrade your existing repo in one pass:
Read `MASTER_SPEC_V2.md` carefully. We are upgrading our existing v1 AegisGraph codebase to implement all 6 high-priority production upgrades without breaking existing working endpoints. Execute the following changes across backend and frontend:

1. **Deterministic Service Physics Simulator (`backend/simulator.py` & `backend/seed_graph.py`):**
   - Update `seed_graph.py` so every `:Service` node has physical config properties (`timeout_ms`, `max_pool_size`, `circuit_breaker`, `base_processing_ms`, `current_load_rps`) and computed telemetry (`p99_latency_ms`, `error_rate`, `status`).
   - Implement `recalculate_graph_telemetry(graph_name)` in `backend/simulator.py`. Never hardcode `SET s.status = 'HEALTHY'`. Derive `p99_latency_ms`, `error_rate`, and `status` mathematically from the `:DEPENDS_ON` graph topology and physical configs.
   - Seed the initial fault so `token-auth-service` (`timeout_ms: 150`, `max_pool_size: 20`, `circuit_breaker: false`) causes a cascading ~58% error rate on `checkout-api`.

2. **Model-Directed MCP Investigation Loop (`backend/mcp_server.py` & `backend/agents.py`):**
   - Expose the 7 granular MCP tools defined in Section 3, Module 2 of `MASTER_SPEC_V2.md`.
   - Ensure `inspect_service_telemetry_and_frontier` returns unexplored edge counts so the LLM dynamically chooses its own sequence of MCP tool calls rather than running a fixed Python list of queries.
   - Ensure `simulate_config_mutation_in_sandbox` clones the service subgraph into `vortexpay_sandbox`, runs `recalculate_graph_telemetry("vortexpay_sandbox")`, and returns the simulated metric delta before touching `vortexpay_prod`.

3. **Versioned Playbooks with Precondition Gate & Verified Compiler (`backend/playbook_engine.py`):**
   - Before starting an investigation, query FalkorDB for an active `:Playbook` matching the `:SymptomSignature`.
   - Verify preconditions against the live graph: (a) the playbook's `required_decision_id` must still have `status = 'ACTIVE'`, and (b) the upstream `:DEPENDS_ON` `topology_hash` must match.
   - If preconditions pass, execute the saved `:ActionStep` args, run `recalculate_graph_telemetry("vortexpay_prod")`, and verify `error_rate < 0.01`.
   - If preconditions fail (e.g., after `DEC-02` is superseded by `DEC-03`), log `REJECTED_STALE_POLICY`, run a full model-directed investigation, and compile the newly verified action into `Playbook v2` with a `[:SUPERSEDES_PLAYBOOK]` edge pointing to `v1`.

4. **Durable Graph Checkpointing & Crash Recovery (`backend/orchestrator.py` & `backend/main.py`):**
   - Persist every investigation step into `(:InvestigationRun)-[:EXECUTED_STEP]->(:ToolTrace)` in FalkorDB, including serialized `messages_checkpoint_json`, token counts, LLM call counts, and cumulative FalkorDB execution ms.
   - Support an `interrupt_at_step=3` parameter that simulates a backend worker crash mid-investigation (setting `status = 'INTERRUPTED_CRASH'`), and create `POST /api/runs/{run_id}/resume` that reloads the state strictly from FalkorDB and finishes the investigation from Step 4.

5. **Frontend Telemetry & Evidence Comparison Panel (`frontend/`):**
   - Add live service metric bars (`error_rate %` and `p99_latency_ms`) showing the physics simulator output.
   - Add an "Evidence & Benchmark Panel" comparing Cold Discovery vs. Warm Replay vs. Rejected Replay (showing Execution Mode, Precondition Verdict, LLM Calls, MCP Calls, Tokens, FalkorDB Latency ms, Duration, and Pre/Post Error Rate).
   - Add a "Simulate Backend Crash at Step 3" toggle and a "Resume Interrupted Run from FalkorDB" button.

6. The Updated 5-Click Demo Sequence (How to Show All 6 Upgrades in 180 Seconds)
Once Codex completes this upgrade, your demo video will follow this unassailable 5-step arc:
 * Click 1 — Trigger Incident (Cold Discovery + Crash Recovery Proof):
   * Enable "Simulate Crash at Step 3" and click "Investigate Checkout Incident".
   * The model dynamically chooses MCP tools (inspect_service_telemetry_and_frontier \rightarrow traverse_dependency \rightarrow inspect_recent_prs). At Step 3, the backend crashes!
   * Click "Resume from FalkorDB State". The backend reads (:InvestigationRun) from FalkorDB, resumes at Step 4, tests the fix in vortexpay_sandbox, applies max_pool_size=120, circuit_breaker=true to vortexpay_prod, watches the physics simulator drop checkout-api error rate from 58.4% to 0.2%, and compiles Playbook v1 linked to DEC-02.
 * Click 2 — Re-Trigger Incident (Warm Replay):
   * Re-inject the fault and click "Investigate".
   * Commander checks Playbook v1 preconditions (DEC-02 == ACTIVE, topology_hash == MATCH). It skips the 6-step discovery, applies the verified config in 1 step (1.4s, 87% fewer tokens), and restores health.
 * Click 3 — Inject Policy Contradiction (DEC-03 Supersedes DEC-02):
   * Click "Inject Security Directive (Slack)": Priya Nair (Security Architect) mandates that circuit_breaker fallback mode is banned unless timeout_ms is also raised to 450ms (DEC-03 :SUPERSEDES DEC-02).
 * Click 4 — Re-Trigger Incident (Rejected Stale Playbook \rightarrow Compile Playbook v2):
   * Trigger the incident again.
   * Commander runs the Precondition Gate and flashes red: REJECTED PLAYBOOK v1: Governing Decision DEC-02 is SUPERSEDED by DEC-03.
   * The agent automatically drops back into model-directed investigation, reads DEC-03, tests timeout_ms=450, max_pool_size=120 in the sandbox, verifies recovery in prod, and compiles Playbook v2 ([:SUPERSEDES_PLAYBOOK]-> v1).
 * Click 5 — Open the Evidence Comparison Panel:
   * Show the judges the side-by-side table comparing Discovery (6 steps) vs. Warm Replay (1 step) vs. Rejected Stale Replay \rightarrow v2 Recompilation.