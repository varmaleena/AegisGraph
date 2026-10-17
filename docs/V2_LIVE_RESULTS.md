# V2 live Gemini validation

All three runs used real FalkorDB; discovery/reinvestigation used real Gemini tool calling over MCP.
Warm replay used no model calls. These are single local observations, not performance guarantees.

| Mode | Model calls | MCP calls | Provider tokens | Active duration ms | Error before | Error after |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| DISCOVERY | 8 | 8 | 31874 | 61128 | 57.21% | 0.34% |
| WARM_REPLAY | 0 | 1 | 0 | 823 | 57.21% | 0.34% |
| REJECTED_REPLAY_REINVESTIGATION | 8 | 8 | 28043 | 30394 | 57.21% | 0.20% |

The first discovery deliberately stopped at step 3 and resumed from FalkorDB.
One transient MCP-wrapped interruption was diagnosed during discovery; the saved run completed after resume.
Reinvestigation rejected Playbook v1 because DEC-02 was SUPERSEDED by DEC-03.
Gemini returned HTTP 429 during reinvestigation. After a single cooldown, the same run resumed and completed.
No provider or billing fallback was used. Quota downtime is excluded from active-duration metrics.
The compiler created v2 from the exact verified production mutation and linked SUPERSEDES_PLAYBOOK to v1.

Regression verification after the error-handling fix: 34 tests passed in the Linux Docker backend.
Raw measured evidence: V2_LIVE_VERIFICATION.json and V2_LIVE_EVENTS.json.
API credentials are not included in either artifact.

## Exact configurations selected by the live model
- Playbook v1 under DEC-02: timeout 150ms, max_pool_size 100, circuit breaker enabled.
- Playbook v2 under DEC-03: timeout 500ms, max_pool_size 100, circuit breaker enabled.
These values came from model-selected tool arguments, not a hardcoded 120-pool/450ms template.
The model selected a different tool order during reinvestigation: PageRank before PR inspection.
