# Graph Hacks compliance and track audit
Checked October 17, 2026 against the official public pages:
- Rules: https://www.wemakedevs.org/hackathons/falkordb/rules
- Track descriptions and FAQ: https://www.wemakedevs.org/hackathons/falkordb
- Schedule: https://www.wemakedevs.org/hackathons/falkordb/schedule

This is an implementation audit, not a guarantee of eligibility or organizer approval.

## Required submission and technology criteria

| Requirement | Status | Evidence / remaining action |
| --- | --- | --- |
| Rule 2: FalkorDB primary and central | Verified locally | Six Cypher tools, policy history, Tasks, Hypotheses, Sessions, Events and playbooks use FalkorDB. |
| Rule 3: graph does real work | Verified locally | Stopping the real container makes all seven data-dependent API endpoints return 503. Static UI shell remains available. |
| Rule 4: deployment platform | Compatible | Docker/self-hosted/Cloud and any app platform are allowed. Railway app services plus FalkorDB Cloud would be acceptable platform choices. |
| Rule 5: declare tracks | Prepared | README declares Tracks 01, 02 and 03. Submission form is not completed. |
| Rule 6: permitted data | Verified for fixture | VortexPay and all people/PRs/documents are synthetic. No connected private company data. |
| Rule 8: main work begins during event | Consistent with local records | Scaffolding and checkpoints date from October 15 onward; retain history/evidence. |
| Rule 10: public source repository | Missing | Source exists locally; no public repository has been supplied or created. A source ZIP does not replace this requirement. |
| Rule 10: setup and graph-model README | Complete locally | README includes Compose instructions, schema, environment setup, and implementation limits. |
| Rule 10: Cypher/algorithms | Complete locally | Six executable query blocks plus original spec queries, shortestPath, PageRank and shadow connectivity queries. |
| Rule 10: working demo video | Draft evidence only | docs/demo.webm is a short silent automated browser check. Prepare an understandable submission walkthrough and a shareable video URL. |
| Rule 10: deployment or complete local instructions | Local path verified | Full Docker stack builds and starts. No public deployment URL exists. Official FAQ prefers deployment but accepts local setup if deployment is not possible. |
| Rule 11: AI disclosure | Written | README discloses Codex implementation/testing work and participant-supplied architecture. |
| Rules 12–13: participant understanding and meaningful contribution | Requires participant verification | Participant must review and explain the model, queries, architecture and decisions. Automated tests cannot establish this on their behalf. |
| Registration, team size and membership | Unverified | Registration not inspected; team must meet the official solo/up-to-four requirement and one-team-per-participant rule. |
| Deadline | Pending human submission | October 18, 2026 at 11:59 PM IST. |

## Track fit versus limitations

### Track 01: Agents That Act on Connected Data
Demonstrated: dependency traversal, PR/author/team attribution, PageRank, parameterized tools,
shadow action simulation and policy-constrained synthetic remediation.

Limitations:
- Specialist orchestration is scripted and synchronous; there is no model-directed plan/tool selection.
- MCP server exposes six tools, but the running orchestrator calls Python functions directly.
- Remediation changes synthetic graph state, not external infrastructure.
- Checkout-to-auth is one direct service edge; do not describe it as a three-hop service path.
  Longer paths exist from web-storefront or through payment-orchestrator.
- Shadow reachability checks topology safety; they do not simulate real queueing/timeout behavior.

Assessment: graph-work evidence is strong; autonomous-agent evidence is limited.
The public rules do not explicitly mandate an LLM. Do not equate that with organizer endorsement
of a fixed workflow as a strong AI-agent entry.

### Track 02: Agent Memory and Coordination
Demonstrated: persisted sessions/events, graph tasks and hypotheses, a compiled allowlisted
procedure, fresh-interpreter replay, tenant separation and conflicting-operation rejection.

Limitations:
- Writes are serialized by a tenant graph lease; high-concurrency agent coordination is not demonstrated.
- Agents are role-specific components of a synchronous loop, not independent asynchronous workers.
- The learned playbook contains one synthetic remediation action, not an arbitrary generalized workflow compiler.

Assessment: currently the clearest demonstrated track fit, especially procedural replay.

### Track 03: Company Brain
Demonstrated: people/team ownership, PR and document provenance, contradictory policy revision,
effective/recorded-time lookup and supersession lineage.

Limitations:
- The ingestion and question-answering surface covers one fixed synthetic incident/policy scenario.
- The composer records a note and starts that workflow; it is not general company Q&A.
- No automatic extraction or semantic contradiction detection from arbitrary text is implemented.

Assessment: strong narrow temporal/provenance demonstration, limited breadth.

## Highest-priority remaining actions
1. Publish source to a public repository and add author/team identity.
2. Review and independently run the demo; prepare a clear working video and submission links.
3. If improving agent capability before submission, add verified model-directed tool selection
   grounded in these graph tools; never describe the current fixed loop as autonomous LLM reasoning.
4. Deploy if practical. Railway frontend/backend plus FalkorDB Cloud is an option, not a rule.
   Add access control before making write APIs public.
5. Register/confirm team details and submit with the selected tracks before the deadline.

## Verification already completed
22 real FalkorDB backend integration tests, actual database-stop behavior, Windows and Linux Docker
execution, production frontend build, zero npm audit findings, and a complete Edge demo flow.
CI is supplied but has not executed on a public GitHub repository.

## V2 update
The V2 implementation replaces the main UI's scripted investigation path with provider
tool calling over real MCP, adds measured physics and precondition-checked versioned memory,
and persists step-level checkpoints with fresh-process resume tests.
Live-provider verification remains pending model credentials. Earlier scripted-loop limitations
describe legacy endpoints; do not use fixture tests as evidence of real provider performance.

## Live V2 validation update
Real Gemini-directed tool selection, step-3 interruption/resume, warm replay, stale-policy
rejection and v2 recompilation have now passed. See V2_LIVE_RESULTS.md.
Warm replay used 0 model calls, 1 MCP call and 823ms in one observed run.
A real HTTP 429 interruption was recovered from the saved checkpoint after cooldown.
Public repository, submission video/narration, participant review and deployment status are separate submission items.
