
# MASTER ENGINEERING SPECIFICATION: *AegisGraph*

*Subtitle:* Bi-Temporal Company Brain, Multi-Agent Blackboard & Procedural Memory Engine on FalkorDB
*Hackathon:* Graph Hacks: Context for AI Agents (Powered by FalkorDB)
*Target Tracks:*

1. *Track 01:* Agents That Act on Connected Data
2. *Track 02:* Agent Memory and Coordination
3. *Track 03:* Company Brain

---

## 1. Executive Summary & Problem Statement

### 1.1 The Real Problem in Production Agentic AI

Enterprise AI agents fail in production not because LLMs lack reasoning capability, but because their *context layer is structurally flat, temporally blind, and procedurally amnesiac*:

1. *Epistemic Drift & Contradiction (Track 03 Problem):* Company knowledge is non-stationary. An architecture doc in Confluence states payment-service uses Retry-Policy-v1. Two weeks later, a developer merges PR #402 changing the timeout, and a Staff Engineer states in Slack that Retry-Policy-v1 is deprecated due to cascading failures. Vector databases retrieve all three chunks with equal cosine similarity, causing the agent to hallucinate or follow outdated rules.
2. *Multi-Hop Blindness & Unsafe Actions (Track 01 Problem):* When an incident hits or a system change is proposed, standard agents cannot deterministically compute a 5-hop blast radius across microservices, commits, and human owners, nor can they safely simulate the topological impact of an action before executing it.
3. *Procedural Amnesia & State Silos (Track 02 Problem):* When multiple agents collaborate, they pass ephemeral JSON blobs in memory. Furthermore, when an agent successfully resolves a complex 5-step incident in Session 1, that workflow evaporates. In Session 2, the agent wastes tokens re-discovering the exact same reasoning path from scratch.

### 1.2 The Solution: *AegisGraph*

*AegisGraph* is an autonomous Organizational Intelligence and Site Reliability Agent Triad powered *100% by FalkorDB. It uses **zero secondary databases* (no Postgres, no SQLite, no standalone Vector DB). If FalkorDB is turned off, the system cannot store state, coordinate agents, resolve policies, or execute tools—strictly satisfying *Hackathon Rule 3*.

AegisGraph introduces four technical innovations on top of FalkorDB:

1. *Bi-Temporal Belief Revision Graph (Company Brain):* Every organizational decision and fact carries valid_from and valid_to timestamps plus [:SUPERSEDES {reason}] edges. The agent knows what is true now, what used to be true, and who changed it and why.
2. *Multi-Graph Counterfactual Sandbox (Act on Connected Data):* Uses FalkorDB’s lightweight multi-graph tenancy (db.select_graph("vortexpay_prod") vs. db.select_graph("vortexpay_sandbox_sim")) to clone subgraphs in milliseconds and simulate the blast radius of an action using algo.pageRank and shortestPath before acting.
3. *Executable Procedural Subgraphs (Agent Memory):* When an agent resolves an incident in Session 1, it compiles the winning sequence of MCP tool calls into a persistent (:SymptomSignature)-[:TRIGGERS_PLAYBOOK]->(:Playbook)-[:STEP]->(:ActionStep) subgraph. In Session 2, it traverses and executes this compiled graph directly.
4. *Graph-Native Blackboard Coordination:* Three specialized agents (*Scribe, **Navigator, **Commander*) coordinate asynchronously by reading and mutating (:Task) and (:Hypothesis) nodes directly inside FalkorDB.

---

## 2. Recommended Tech Stack (Optimized for AI Coding Assistants)

This stack is deterministic, strongly typed, and designed so Codex/Antigravity can generate and verify it cleanly:

* *Primary Graph Database:* *FalkorDB* (docker run -p 6379:6379 -p 3000:3000 falkordb/falkordb:latest locally; *FalkorDB Cloud* for live deployment).
* *Backend & Agent Runtime:* *Python 3.11+* with *FastAPI*
* falkordb (Official Python client)
* mcp / fastmcp (Model Context Protocol server exposing FalkorDB tools to agents)
* openai / litellm / langgraph (Orchestrating the 3 agents with structured outputs)
* pydantic (Strict schema validation for graph entities and tool calls)


* *Frontend (The "Judge-Winning" Split-Screen UI):* *Next.js 14+ (App Router, TypeScript, Tailwind CSS, Lucide Icons)*
* react-force-graph-2d (Live interactive canvas rendering FalkorDB nodes/edges and pulsing active Cypher paths in real time)
* framer-motion (Smooth animations for real-time agent handoffs and trace inspection)



---

## 3. System Architecture & End-to-End Data Flow

text
+-----------------------------------------------------------------------------------+
|                        NEXT.JS SPLIT-SCREEN FRONTEND                              |
|  [Left Panel: Multi-Agent Command Center]   [Right Panel: Live FalkorDB Canvas]   |
|  - Chat & Incident Trigger Controls         - Real-time Force-Directed Graph      |
|  - Session 1 vs Session 2 Memory Toggle     - Pulsing Path Trace Inspector        |
|  - Multi-Tenant Switcher (Prod / Sandbox)   - Cypher Query + Latency Badge (ms)   |
+------------------------------------+----------------------------------------------+
                                     | REST / SSE Streaming
                                     v
+-----------------------------------------------------------------------------------+
|                     FASTAPI + MULTI-AGENT ORCHESTRATOR                            |
|                                                                                   |
|  1. SCRIBE AGENT (Track 3: Company Brain)                                         |
|     - Ingests Docs, PRs, Slack threads -> Detects policy contradictions           |
|     - Writes Bi-Temporal (:Decision)-[:SUPERSEDES]->(:Decision) edges             |
|                                                                                   |
|  2. NAVIGATOR AGENT (Track 1: Connected Action)                                   |
|     - Executes Multi-Hop Root Cause, PageRank & Shadow-Graph Simulation           |
|     - Writes (:Hypothesis) nodes to FalkorDB Blackboard                           |
|                                                                                   |
|  3. COMMANDER AGENT (Track 2: Memory & Coordination)                              |
|     - Checks FalkorDB for existing (:Playbook) procedural subgraphs               |
|     - Executes remediation & compiles new successful runs into (:Playbook) nodes  |
+------------------------------------+----------------------------------------------+
                                     | Model Context Protocol (MCP Tools)
                                     v
+-----------------------------------------------------------------------------------+
|                        FALKORDB INSTANCE (Single Source of Truth)                 |
|  - Graph 1: `vortexpay_prod` (Company Brain + Blackboard + Episodic/Procedural)   |
|  - Graph 2: `vortexpay_sandbox` (Cloned Ephemeral Graph for Action Simulation)    |
|  - Graph 3: `tenant_beta` (Demonstrates Multi-Tenant Isolation)                   |
+-----------------------------------------------------------------------------------+



---

## 4. The Complete FalkorDB Data Model (Cypher Schema)

All state lives inside FalkorDB across *four logical subgraphs* within the active tenant graph (vortexpay_prod).

### 4.1 Node Labels & Properties

1. *Company Brain Nodes (Track 03)*
* (:Person {id: STRING, name: STRING, role: STRING, team: STRING, handle: STRING})
* (:Team {id: STRING, name: STRING, oncall_channel: STRING})
* (:Service {id: STRING, name: STRING, tier: INT, language: STRING, status: STRING, error_rate: FLOAT})
* (:PR {id: STRING, title: STRING, commit_sha: STRING, timestamp: INT, files_changed: STRING})
* (:Document {id: STRING, title: STRING, doc_type: STRING, url: STRING, updated_at: INT})
* (:Decision {id: STRING, topic: STRING, summary: STRING, source: STRING, valid_from: INT, valid_to: INT, status: STRING}) (Note: valid_to = 0 means currently active; valid_to > 0 means superseded).


2. *Multi-Agent Blackboard Nodes (Track 02 Coordination)*
* (:Incident {id: STRING, title: STRING, error_signature: STRING, severity: STRING, status: STRING, created_at: INT})
* (:Hypothesis {id: STRING, agent: STRING, summary: STRING, confidence: FLOAT, verified: BOOLEAN, cypher_evidence: STRING})


3. *Episodic & Procedural Memory Nodes (Track 02 Memory)*
* (:Session {id: STRING, started_at: INT, user_id: STRING, summary: STRING})
* (:SymptomSignature {id: STRING, error_code: STRING, affected_service: STRING})
* (:Playbook {id: STRING, name: STRING, created_from_incident: STRING, success_count: INT, avg_resolution_ms: INT})
* (:ActionStep {id: STRING, step_order: INT, mcp_tool: STRING, tool_args_json: STRING, expected_outcome: STRING})



### 4.2 Relationship Types (Edges)

cypher
// Layer 1: Company Brain Relationships
(:Person)-[:MEMBER_OF]->(:Team)
(:Team)-[:OWNS]->(:Service)
(:Person)-[:AUTHORED]->(:PR)
(:PR)-[:MODIFIED]->(:Service)
(:Service)-[:DEPENDS_ON {criticality: STRING, call_type: STRING}]->(:Service)
(:Decision)-[:GOVERNS]->(:Service)
(:Decision)-[:DOCUMENTED_IN]->(:Document)
(:Decision)-[:DECIDED_BY]->(:Person)
(:Decision)-[:SUPERSEDES {reason: STRING, timestamp: INT}]->(:Decision)

// Layer 2: Multi-Agent Blackboard Relationships
(:Incident)-[:AFFECTS]->(:Service)
(:Incident)-[:HAS_HYPOTHESIS]->(:Hypothesis)
(:Hypothesis)-[:POINTS_TO_PR]->(:PR)
(:Hypothesis)-[:POINTS_TO_DECISION]->(:Decision)

// Layer 3 & 4: Episodic & Procedural Memory Relationships
(:Session)-[:INVESTIGATED]->(:Incident)
(:SymptomSignature)-[:TRIGGERS_PLAYBOOK]->(:Playbook)
(:Playbook)-[:HAS_STEP {order: INT}]->(:ActionStep)
(:ActionStep)-[:NEXT_STEP]->(:ActionStep)



---

## 5. Core Cypher Queries & FalkorDB Algorithms (Rule 10 Deliverable)

Your backend *must* expose these 6 deterministic Cypher/Algorithm functions inside backend/mcp_tools.py and list them verbatim in your README.md.

### Tool 1: trace_root_cause_and_blast_radius(service_name: str)

Uses shortestPath to connect a failing service to recent upstream PRs and computes downstream impact + subject matter expert ownership:

cypher
MATCH (failing:Service {name: $service_name})
MATCH (upstream:Service)<-[:MODIFIED]-(pr:PR)<-[:AUTHORED]-(dev:Person)
MATCH p = shortestPath((failing)-[:DEPENDS_ON*0..5]->(upstream))
OPTIONAL MATCH (downstream:Service)-[:DEPENDS_ON*1..4]->(failing)
OPTIONAL MATCH (team:Team)-[:OWNS]->(upstream)
RETURN 
  [n IN nodes(p) | n.name] AS dependency_path,
  upstream.name AS root_service,
  pr.id AS suspect_pr,
  pr.title AS pr_title,
  dev.name AS author_name,
  dev.handle AS author_handle,
  team.name AS owning_team,
  collect(DISTINCT downstream.name) AS downstream_blast_radius
ORDER BY length(p) ASC, pr.timestamp DESC
LIMIT 3



### Tool 2: compute_service_criticality_pagerank()

Uses FalkorDB’s native algo.pageRank procedure to identify architectural bottlenecks:

cypher
CALL algo.pageRank('Service', 'DEPENDS_ON') YIELD node, score
RETURN node.name AS service_name, node.tier AS tier, node.status AS status, score AS pagerank_score
ORDER BY pagerank_score DESC
LIMIT 10



### Tool 3: resolve_bitemporal_policy(service_name: str)

Detects active vs. superseded company decisions and returns the full contradiction lineage:

cypher
MATCH (s:Service {name: $service_name})<-[:GOVERNS]-(active:Decision {status: 'ACTIVE'})
OPTIONAL MATCH (active)-[:DECIDED_BY]->(author:Person)
OPTIONAL MATCH path = (active)-[:SUPERSEDES*1..5]->(old:Decision)
RETURN 
  active.id AS active_decision_id,
  active.summary AS current_policy,
  active.source AS current_source,
  active.valid_from AS valid_from,
  author.name AS decided_by,
  [d IN nodes(path) WHERE d <> active | {id: d.id, summary: d.summary, source: d.source, valid_to: d.valid_to}] AS superseded_history



### Tool 4: ingest_and_supersede_decision(...)

Used by the *Scribe Agent* when a new Slack message or PR overrides an older policy:

cypher
MATCH (s:Service {name: $service_name})<-[:GOVERNS]-(old:Decision {topic: $topic, status: 'ACTIVE'})
MATCH (p:Person {name: $person_name})
SET old.status = 'SUPERSEDED', old.valid_to = $timestamp
CREATE (new:Decision {
  id: $new_id,
  topic: $topic,
  summary: $new_summary,
  source: $source,
  valid_from: $timestamp,
  valid_to: 0,
  status: 'ACTIVE'
})
CREATE (new)-[:GOVERNS]->(s)
CREATE (new)-[:DECIDED_BY]->(p)
CREATE (new)-[:SUPERSEDES {reason: $reason, timestamp: $timestamp}]->(old)
RETURN new.id AS created_decision, old.id AS superseded_decision



### Tool 5: lookup_procedural_playbook(error_code: str, service_name: str)

Used by the *Commander Agent* at the start of any session to check if the graph already knows how to solve this exact problem:

cypher
MATCH (sig:SymptomSignature {error_code: $error_code, affected_service: $service_name})-[:TRIGGERS_PLAYBOOK]->(pb:Playbook)
MATCH (pb)-[r:HAS_STEP]->(step:ActionStep)
RETURN 
  pb.id AS playbook_id,
  pb.name AS playbook_name,
  pb.success_count AS prior_successes,
  step.step_order AS step_order,
  step.mcp_tool AS tool_name,
  step.tool_args_json AS tool_args,
  step.expected_outcome AS outcome
ORDER BY step.step_order ASC



### Tool 6: simulate_action_in_shadow_graph(target_service: str, action: str)

Demonstrates FalkorDB’s multi-graph capability by cloning the dependency topology into vortexpay_sandbox, isolating the node, and checking which Tier-1 services lose connectivity:

cypher
// Executed on graph: vortexpay_sandbox
MATCH (target:Service {name: $target_service})
MATCH (caller:Service)-[:DEPENDS_ON*1..4]->(target)
WHERE caller.tier = 1
RETURN count(DISTINCT caller) AS impacted_tier1_services, collect(DISTINCT caller.name) AS impacted_names



---

## 6. Synthetic Dataset Specification ("VortexPay") — Rule 6 Compliant

To guarantee a captivating demo without violating Rule 6 (no private data), backend/seed_graph.py must deterministically populate the vortexpay_prod graph with a rich fintech scenario:

* *Teams (3):* Core-Payments, Identity-Platform, Checkout-Experience
* *Engineers (6):*
* Sarah Chen (Staff Engineer, Identity-Platform)
* Marcus Vance (Senior SRE, Core-Payments)
* Elena Rostova (Backend Eng, Identity-Platform)
* Devon Brooks (Frontend Lead, Checkout-Experience)
* Priya Nair (Security Architect, Identity-Platform)
* Alex Rivera (DevOps, Core-Payments)


* *Microservices (8 Connected Nodes):*
* web-storefront (Tier 1) $\rightarrow$ checkout-api (Tier 1) $\rightarrow$ payment-orchestrator (Tier 1)
* payment-orchestrator $\rightarrow$ fraud-engine (Tier 2), ledger-db-proxy (Tier 1), and token-auth-service (Tier 1)
* checkout-api $\rightarrow$ token-auth-service (Tier 1)
* token-auth-service $\rightarrow$ redis-session-cluster (Tier 1)


* *Planted Multi-Hop Mystery (For Track 1 & 3 Demo):*
* *Old Confluence Doc (DOC-101, 30 days ago):* States token-auth-service uses a connection pool timeout of 5000ms (DEC-01).
* *Slack Thread (SLACK-882, 2 hours ago):* Sarah Chen posts that under flash-sale load, 5000ms causes thread starvation, so she approved lowering timeout to 150ms and enabling strict circuit breaking (DEC-02, which :SUPERSEDES DEC-01).
* *Recent PR (PR-409, 45 mins ago):* Authored by Elena Rostova modifying token-auth-service to set timeout to 150ms, accidentally triggering ERR_AUTH_POOL_EXHAUSTED in checkout-api (2 hops away).



---

## 7. Repository Directory Structure

Instruct Codex/Antigravity to scaffold this exact monorepo layout:

text
aegis-graph/
├── docker-compose.yml              # Runs falkordb/falkordb:latest + backend + frontend
├── .env.example                    # FALKORDB_HOST, FALKORDB_PORT, OPENAI_API_KEY
├── README.md                       # Rule 10 compliant README with Schema, Cypher, Setup, AI Disclosure
├── backend/
│   ├── requirements.txt            # fastapi, uvicorn, falkordb, openai, pydantic, mcp
│   ├── db.py                       # FalkorDB connection manager + Multi-Graph switcher
│   ├── seed_graph.py               # Populates VortexPay 4-layer graph + planted mystery
│   ├── mcp_server.py               # FastMCP server wrapping the 6 core Cypher/Algo tools
│   ├── agents.py                   # Scribe, Navigator, and Commander agent loops + Graph Blackboard
│   └── main.py                     # FastAPI endpoints (/graph, /chat, /simulate, /ingest-contradiction, /reset-session)
└── frontend/
    ├── package.json                # next, react, react-force-graph-2d, lucide-react, tailwindcss
    └── src/
        ├── app/
        │   ├── page.tsx            # Main Split-Screen Command Center
        │   └── layout.tsx
        └── components/
            ├── GraphCanvas.tsx     # Live Force-Graph with node color-coding & path highlighting
            ├── AgentConsole.tsx    # Chat + Multi-Agent Blackboard Stepper (Scribe -> Navigator -> Commander)
            ├── TraceInspector.tsx  # Displays exact Cypher query executed, ms latency, and traversed nodes
            └── HeaderBar.tsx       # Tenant Graph Switcher (vortexpay_prod | vortexpay_sandbox) + Session Reset



---

## 8. Step-by-Step Build Guidelines for Codex / Antigravity

When you start coding at *12:01 AM IST on Oct 15*, execute these 5 prompts sequentially in your AI coding environment:

### Phase 1: Infrastructure & Deterministic Graph Seeder (Hours 0–4)

> *Prompt for Codex/Antigravity:*
> "Read MASTER_SPEC.md Sections 4, 5, and 6. Create docker-compose.yml running falkordb/falkordb:latest on ports 6379 and 3000. Then create backend/db.py and backend/seed_graph.py using the official falkordb Python client. Implement the exact 4-layer VortexPay schema (Persons, Teams, Services, PRs, Decisions with :SUPERSEDES edges, Incidents, Hypotheses, SymptomSignatures, Playbooks, ActionSteps). Ensure every query logs execution time in milliseconds from FalkorDB metadata."

### Phase 2: The FalkorDB MCP Server & Algorithm Tools (Hours 4–12)

> *Prompt for Codex/Antigravity:*
> "Read MASTER_SPEC.md Section 5. Create backend/mcp_server.py implementing all 6 tools (trace_root_cause_and_blast_radius, compute_service_criticality_pagerank, resolve_bitemporal_policy, ingest_and_supersede_decision, lookup_procedural_playbook, and simulate_action_in_shadow_graph). Each tool must return a structured dictionary containing: data (the result rows), cypher_executed (exact Cypher string), execution_time_ms (from FalkorDB query stats), and highlighted_node_ids (list of node IDs touched so the frontend can animate them)."

### Phase 3: The 3-Agent Orchestrator & Procedural Compiler (Hours 12–24)

> *Prompt for Codex/Antigravity:*
> "Create backend/agents.py and backend/main.py. Implement the 3-agent triad (Scribe, Navigator, Commander). Crucial rule: Do not store conversation state or agent handoffs in Python memory—write (:Session), (:Incident), and (:Hypothesis) nodes directly into FalkorDB after every agent step. When Commander resolves an incident in Session 1, automatically write a (:SymptomSignature)-[:TRIGGERS_PLAYBOOK]->(:Playbook)-[:HAS_STEP]->(:ActionStep) subgraph into FalkorDB so Session 2 resolves the same error signature in a single hop."

### Phase 4: The "Judge-Winning" Split-Screen UI (Hours 24–40)

> *Prompt for Codex/Antigravity:*
> "Build the Next.js frontend in frontend/. Create a dark-mode engineering command center with two halves: Left side has quick-action demo buttons ('1. Inject Slack Policy Contradiction', '2. Trigger Checkout Latency Incident [Session 1]', '3. Wipe Chat & Re-Trigger Incident [Session 2 Procedural Fast-Path]', '4. Run Shadow-Graph Rollback Simulation'). Right side renders GraphCanvas.tsx using react-force-graph-2d. Color-code nodes by layer (Services=Blue, Decisions=Amber, PRs=Purple, Playbooks=Emerald, Incidents=Red). Whenever an agent runs a Cypher tool, pulse the highlighted_node_ids on the canvas and show the exact Cypher query + millisecond latency in TraceInspector.tsx."

### Phase 5: Deployment, README & Demo Polish (Hours 40–60)

1. *Cloud Deployment (Rule 10):* Sign up for a free *FalkorDB Cloud* instance, put the connection URI in your .env, run python backend/seed_graph.py against the cloud instance, and deploy the FastAPI backend + Next.js frontend to Render/Railway/Vercel.
2. *README Verification (Rule 10 & Rule 11):* Ensure your README.md contains:
* Track Declaration: *Track 01, Track 02, and Track 03*
* Live URL + 1-command docker compose up --build local instructions
* ASCII/Mermaid Graph Schema Diagram (from Section 4)
* All 6 Cypher Queries & algo.pageRank / shortestPath blocks (from Section 5)
* *AI Coding Assistant Disclosure (Rule 11):* "This project was architected and verified by [Your Name]. AI coding assistants (Codex / Antigravity / Gemini) were used for boilerplate generation, UI component scaffolding, and Cypher syntax validation in accordance with Rule 11."



---

## 9. How to verify You Will Win (The Pre-Submission Checklist)

Before recording your 3-minute submission video on October 18, run this 4-point audit:

1. *The "Unplug FalkorDB" Test (Rule 3):* If you stop the FalkorDB container, does every single feature fail? Yes—because chat history, agent coordination hypotheses, company policies, and procedural playbooks all live inside FalkorDB.
2. *Visual Proof of Graph Work:* Can a judge watching your video on mute immediately see the graph nodes lighting up as the agent reasons across 4 hops? Yes—via the split-screen Force Graph and Cypher Trace Drawer.
3. *All 3 Tracks Proven in 180 Seconds:*
* Minute 1 (Track 3 - Company Brain): Click "Inject Slack Policy Contradiction" $\rightarrow$ Scribe creates a :SUPERSEDES edge invalidating the old doc.
* Minute 2 (Track 1 - Connected Data): Click "Trigger Incident (Session 1)" $\rightarrow$ Navigator runs shortestPath + algo.pageRank + Shadow Graph Simulation to trace checkout-api failure 3 hops back to Elena Rostova's PR and Sarah Chen's Slack decision.
* Minute 3 (Track 2 - Memory & Coordination): Commander saves the fix as a green (:Playbook) subgraph. Click "New Session" $\rightarrow$ Trigger the alert again $\rightarrow$ Agent immediately executes the compiled (:Playbook) from FalkorDB in 1 step.


4. *Code Understanding (Rule 12):* Read through backend/mcp_server.py and backend/seed_graph.py once it is generated so you can explain every Cypher MATCH, shortestPath, and algo.pageRank call effortlessly if judges ask follow-up questions on Discord.