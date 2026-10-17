# Verification evidence — October 17, 2026

## Passed local and Docker checks
- 22 backend tests against real FalkorDB on Windows and inside the Linux Docker backend: 4 infrastructure, 7 tools, 7 agent, 4 API tests.
- Database-stop check: /health, /graph, /session, /chat, /reset-session,
  /ingest-contradiction and /simulate returned 503. Restart recovered persisted data.
- Frontend TypeScript checks and production build.
- Full Edge workflow: policy injection, investigation, playbook compilation, procedural
  replay, reload persistence, shadow simulation, tenant changes, mobile overflow,
  and no uncaught page errors.
- npm audit: zero findings after patched PostCSS and removing unused Tailwind tooling.

## Fixes found through integration
- FalkorDB shortestPath placement, native graph-list decoding, missing-target rejection.
- Duplicate task edges and Navigator evidence attribution.
- A React effect incorrectly returned the scroll call result, causing browser teardown errors.
- Tenant selection was lost on reload; it now lives in the URL.
- Graph data was recreated on highlight updates, and stale fetches could overwrite a newer view.
- The final System event cleared the useful trace; the UI now keeps the last executed query selected.

The specialist agent loop is deterministic and synchronous; synthetic HEALTHY is graph state,
not a real operational health probe. This is a hackathon demo, not a production SRE integration.
CI is provided but has not run on GitHub. Public repository, author attribution and human review remain pending.

The Docker production frontend build and full Compose startup succeeded. The app remains running locally.

## V2 final verification
33 backend tests pass in the packaged Linux container, including real MCP transport,
derived physics, policy/receipt rejection, cold compilation, warm replay, stale policy
versioning, topology drift, HTTP streaming, missing/placeholder keys, fresh-process
resume and interruption after a verified mutation.
The V2 production frontend build and no-key browser checks pass.
No live provider run has been verified; do not treat fixture token counts as benchmarks.
See docs/V2_WORKFLOW.md for exact formulas, measurement scope, and model setup.

## Live Gemini evidence
Live discovery/crash-resume, warm replay, stale policy rejection and v2 recompilation
all passed. See V2_LIVE_RESULTS.md and V2_LIVE_VERIFICATION.json.
The first run used 8 successful model responses / 8 MCP calls / 31,874 reported tokens.
Warm replay used 0 model responses / 1 MCP call / 0 tokens and 823ms active execution.
Reinvestigation used 8 model responses / 8 MCP calls / 28,043 tokens and saved v2.
A provider 429 was handled by preserving the checkpoint and resuming after cooldown.
