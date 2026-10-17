# Iteration checkpoint — 2026-10-15

The project is scaffolded, not yet a verified working application.

## Completed checks
- Backend imports, FastAPI route registration and FastMCP imports pass.
- Installed FalkorDB 1.8.0 exposes Graph.copy and QueryResult.run_time_ms.
- Frontend TypeScript check passes after correcting TraceInspector JSX.

## Next checkpoint: database infrastructure
- WSL reports not installed.
- Docker was not found on PATH or in its standard system install location.
- Install WSL 2 and Docker Desktop; start only the falkordb Compose service.
- Verify redis-cli PING and GRAPH.QUERY before seeding.
- Then verify fixture counts, dependencies, policy and isolation between tenants.

## Pending checks, in order
1. Seed on real FalkorDB; check deterministic repeat runs and graph schema.
2. Execute each of the six tools against FalkorDB; verify temporal boundaries,
   PageRank, root-cause paths, clone isolation and before/after connectivity.
3. Session 1 investigation, durable handoffs, Session 2 replay, restart persistence.
4. API SSE framing, failure paths, and unplug-FalkorDB behavior.
5. Frontend production build, browser interaction, tenant changes and trace animation.

## Known review items
- npm audit reports a transitive PostCSS vulnerability in the selected Next.js
  release; resolve during the frontend dependency checkpoint.
- Shadow clone existence check needs bytes/string normalization validation.
- Timeline versioning and shortestPath aggregation require real Cypher execution.
- The three specialist agents currently use deterministic orchestration, not LLM
  reasoning or asynchronous workers. Do not present them as such.
- Deployment, full submission README and video are not complete.

## Infrastructure installation update
- Microsoft WSL 2.7.13 installed successfully; default WSL version 2.
- Docker Desktop 4.95.0 installed successfully; Docker CLI 29.8.2 responds.
- Docker Desktop launched; engine is not yet verified.
- Windows CBS RebootPending is true after optional-feature setup. Restart Windows before continuing.
- Next action: check docker info, run docker compose up -d falkordb, then verify PING and GRAPH.QUERY. Do not start the rest of the stack until the database checkpoint passes.

## Stage 1 verified — 2026-10-15
- Docker Linux engine responds; FalkorDB Compose container is healthy.
- redis-cli PING returned PONG; GRAPH.QUERY executed successfully.
- Seeded both vortexpay_prod and tenant_beta using the official Python client.
- Four integration tests passed: fixture entities/edges, repeat-seed idempotency, tenant isolation, and real database execution metadata.
- Each tenant has 3 teams, 6 people, 8 services, 8 dependency edges, and 8 ownership edges.
- Test command: python -m pytest backend/tests/test_stage1_infrastructure.py -q
- Next checkpoint: execute the six tools independently and repair observed Cypher/simulation failures before agent testing.

## Stage 2 verified — 2026-10-15
- Seven real FalkorDB integration tests passed across all six tools.
- Fixed shortestPath to use WITH, as required by FalkorDB; sorting uses projected aliases.
- Normalized GRAPH.LIST bytes to strings so repeated sandbox simulations can replace their prior clone.
- Unknown target services are rejected before simulation.
- Verified root-cause owner/PR/path, PageRank ordering, effective-time and recorded-time history, idempotent decision ingestion, ordered procedural lookup, safe/unsafe simulations, clone isolation and parameterized input.
- tenant_beta was restored to its initial fixture after the suite; vortexpay_prod was not revised.
- Actual shortest service path checkout-api to token-auth-service is one hop, matching the specified direct dependency.
- Next checkpoint: Session 1 handoffs and remediation, persisted playbook compilation, then Session 2 replay; inspect and fix failures before API/UI testing.

## Stage 3 verified — 2026-10-15
- Seven integration tests passed for agent sessions and coordination.
- Session 1 resolves the synthetic incident, persists hypotheses/tasks/events, and compiles PB-AUTH.
- Session 2 executes from a fresh Python interpreter using FalkorDB procedural memory; no Scribe/Navigator reinvestigation.
- Verified chat reset retains old session events and replay increments success_count.
- Missing policy, disallowed stored tool, wrong stored arguments, and failed postconditions mark the incident FAILED without counting another success.
- Verified graph lease rejects a competing operation and releases after an exception.
- Fixed duplicate HAS_TASK edges and attached PR evidence to Navigator's hypothesis.
- Manual sample observed 184ms for discovery and 19ms for replay; these are single local samples, not benchmark claims.
- Tests restored tenant_beta to its initial seed; vortexpay_prod remains untouched.
- Next checkpoint: API REST/SSE, error propagation, reloadable sessions and unplug-FalkorDB behavior. UI browser validation remains pending.
## Stages 4–5 completed locally — October 17, 2026
- Four API integration checks pass for SSE, reload/reset/replay, failed streams,
  validation, graph snapshots, sandbox reads and CORS.
- Actual database-stop check returned 503 for all seven data-dependent endpoints,
  then recovered persisted data after restart.
- Twenty-two backend tests pass on Windows and inside the Linux Docker backend.
- Frontend production build and TypeScript checks pass; npm audit reports zero findings.
- Full Edge demo checks pass, including tenant persistence on reload, shadow graph,
  mobile overflow and no uncaught page errors.
- Fixed React scroll effect cleanup, tenant URL persistence, graph-data memoization,
  late graph response handling, and final Cypher trace selection.
- Visually reviewed desktop and mobile screenshots.
- Docker Compose builds and runs all services with the seeded FalkorDB instance.
- Added README, graph schema, executable and original Cypher blocks, MCP/setup guidance,
  truthful AI disclosure, CI workflow and participant/demo walkthrough.
- Public repository and author/team identity still require user input.
- No public deployment has been created; complete local setup is the supported path.
- Narrated submission recording and participant verification remain human tasks.

## V2 incremental upgrade — October 17, 2026
- Saved MASTER_SPEC_V2.md unchanged.
- Added deterministic DAG physics, structured DEC-02/DEC-03 bounds and sandbox receipts.
- Added seven granular tools and actual MCP ClientSession/subprocess transport.
- Added Gemini/Groq/OpenAI-compatible model configuration with no scripted production fallback.
- Added versioned playbooks, policy/config/topology gates and exact verified-trace compiler.
- Added graph checkpoints, pending tool state, worker leases, fresh-process resume and idempotent mutation receipts.
- Added /api/runs streaming/resume/cancel, security-policy and evidence endpoints.
- Added live telemetry, comparison panel, crash toggle and graph-backed resume button.
- Preserved V1 endpoints while removing manual healthy-state assignments.
- Browser verified missing-key errors, telemetry, security controls, crash toggle and mobile layout.
- Real-provider runs remain unverified: no real model key is present in local .env.
- Integration fixtures are clearly TEST_FIXTURE; they are not live model benchmark evidence.
Final V2 container regression: 33 passed; Docker frontend production build passed; V2 no-key browser checks passed.

## Live V2 provider checkpoint
- Supplied Gemini key authenticated successfully; stored only in ignored local .env.
- Real Gemini chose 8 MCP tools for cold discovery and 8 for stale-policy reinvestigation.
- Step-3 interruption/resume passed with actual provider messages.
- Warm replay passed with 0 model calls, 0 tokens, 1 MCP call and 823ms active time.
- DEC-03 caused REJECTED_STALE_POLICY; v2 compiled with SUPERSEDES_PLAYBOOK to v1.
- Actual Gemini HTTP429 retained the checkpoint; cooldown/resume completed the same run.
- Wrapped-provider errors are now classified without revealing credential/provider payloads.
- 34 container regression tests passed after the error-reporting fix.
- Detailed measured results are in docs/V2_LIVE_RESULTS.md.
