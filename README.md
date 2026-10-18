# AegisGraph

A graph-backed incident investigator that learns verified recovery playbooks and rejects them when company policy or dependencies change.

**Live app:** https://aegisgraph-sand.vercel.app
**API:** https://aegisgraph-api.onrender.com
**Source:** https://github.com/varmaleena/AegisGraph

## V2 architecture

`POST /api/runs` starts a model-directed MCP loop. The model selects one registered tool per turn; FastAPI persists the conversation, tool evidence and progress in FalkorDB. Scribe, Navigator and Commander identify tool responsibilities in this single orchestrated loop.

- **Bi-temporal decisions:** `Decision` nodes retain valid-time and recorded-time intervals, source documents, authors and supersession lineage. DEC-02 replaces the DOC-101 decision; DEC-03 adds new security bounds.
- **Versioned procedural memory:** successful measured mutations compile into playbooks. Replay checks the active decision, configuration bounds, dependency names and exact dependency edges before applying stored arguments.
- **DAG physics:** service configuration, load and downstream dependencies determine simulated error rates and p99 latency. Telemetry is calculated, not supplied by the model.
- **Shadow execution:** configuration proposals use isolated service topology snapshots. Scenario 04 performs native `GRAPH.COPY`, changes only the sandbox, calculates lost reachability and recomputes physics there.
- **Durable checkpoints:** each completed MCP step and serialized conversation live in the graph. Resume continues the same run after an application interruption without repeating completed steps.
- **Provider resilience:** configurable Gemini key/model routes plus an explicitly configured Groq fallback use bounded retries, 1s/2s backoff and a total selection deadline. Attempt history records provider/model/credential slot without secrets. Explicit OpenAI selection never becomes an automatic paid fallback.

FalkorDB is the sole state store. All company data and infrastructure effects in this demonstration are synthetic.

## Run locally

Requirements: Docker Desktop with Compose, and a tool-calling model API key.

```sh
cp .env.example .env
# Edit .env privately, then:
docker compose up --build -d
```

Open http://localhost:3001. FalkorDB Browser is http://localhost:3000, and API documentation is http://localhost:8000/docs.

For the cloud-verified Groq route:

```env
LLM_PROVIDER=groq
LLM_MODEL=openai/gpt-oss-120b
GROQ_API_KEY=your_private_key
```

For a Gemini-first pool:

```env
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.5-flash
GEMINI_API_KEYS=first_private_key,second_private_key
GEMINI_FALLBACK_MODELS=gemini-2.5-flash-lite
GROQ_API_KEY=optional_private_key
GROQ_MODEL=openai/gpt-oss-120b
```

Alternatively use `GEMINI_API_KEY`, `GEMINI_API_KEY_2` and `GEMINI_API_KEY_3`. Keys from the same Google project share quota. Multiple keys do not increase that project's allowance. Retry-After is respected; a bounded exhausted pool retains the checkpoint for later resume. Model availability and free allowances depend on the provider account. Older retired model IDs can be explicitly configured but are excluded from defaults.

Secrets belong in `.env` locally or server environment settings in Render. Never put them in `NEXT_PUBLIC_*` variables or Git. Free-only deployment instructions are in [docs/FREE_DEPLOYMENT.md](docs/FREE_DEPLOYMENT.md).

## Demonstrate the workflow

1. Scenario 01 ingests the contradiction and exposes its interval/supersession evidence. The live gate shows whether learned memory remains usable.
2. Scenario 02 investigates the injected auth-pool incident through real model-selected MCP tools. Enable the step-3 crash option to demonstrate resume.
3. Scenario 03 injects the recurring incident in a new session and replays the verified playbook with zero model calls.
4. Inject DEC-03 to reject the stale playbook and learn a policy-compliant version.
5. Scenario 04 copies the production graph, isolates auth in the sandbox and streams clone, reachability and derived telemetry evidence. Production configuration is preserved.

The benchmark distinguishes successful model responses, reported tokens, MCP calls, tool database compute and active execution duration. Provider attempt history includes failed requests; their unreported tokens are not invented.

## Verification

The deployed Groq workflow completed discovery, deliberate crash/resume, zero-model-call replay and stale-policy reinvestigation. In the beta tenant, simulated checkout errors fell from 57.21% to 0.34% in discovery and to 0.20% after the security revision. Free-tier 429 responses required cooldown and checkpoint resume during that test.

Historical evidence is retained with the original provider/model labels. See [docs/V2_LIVE_RESULTS.md](docs/V2_LIVE_RESULTS.md) and [docs/DEPLOYED_GROQ_OSS_VERIFICATION.json](docs/DEPLOYED_GROQ_OSS_VERIFICATION.json).

```sh
python -m pytest backend/tests -q
cd frontend
npm run typecheck
npm run build
```

Graph integration tests use the disposable `tenant_beta` graph. Back up any valuable beta history before running them. Provider retry tests use mocked transports and do not spend model quota.

## Deployment boundaries

Vercel serves Next.js; Render runs FastAPI and the MCP subprocess; FalkorDB Cloud hosts the graphs. Render Free can cold-start, and FalkorDB Free lacks persistence on database restart. An application checkpoint cannot survive deletion of the underlying graph. Public model-backed mutation endpoints require access control and usage controls before use outside a controlled hackathon demonstration. This project is a verified demonstration, not a claim of completed production hardening.

## Rule 11 — AI assistance disclosure

The participant directed the architecture, graph model and verification workflow, and validated the hosted setup through deployment and demonstration checks. AI coding assistance was used to implement and revise the backend, UI, tests and documentation. Automated integration checks and live provider runs are documented separately so their evidence can be inspected. The participant is responsible for the submitted work and explaining its design and behavior.
