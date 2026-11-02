# Week 15 run log · 1 – 7 Feb 2027 · Demo path: services, contract test, durable orchestration

**Goal (proposal weeks 15–17):**
- Weeks 15–17 build the demo path, the analyst console, the privacy ledger and X7.
- **Week 15** builds the demo path's transport: the token service and the bank nodes as separate HTTP processes. They exchange only the allowlisted messages, and a contract test shows they emit exactly the same messages as the research harness for the same inputs (engineering acceptance).

**State (2 Nov):** parts 1 and 2 are done here and tested; neither needs anything from your machine. Next: the analyst console and the privacy ledger (week 16), then X7 (week 17).

## What was built

| Item | Where | Notes |
| --- | --- | --- |
| Wire format | `finmesh/services/wire.py` | JSON for the allowlisted messages. The allowlist check runs on both sides. Decoding is strict: expected type, exact field set, declared types (no float or bool posing as an integer), hex bytes |
| Service authentication | `finmesh/services/auth.py` | Each bank signs calls to the token service with an HMAC over bank, time, a one-time nonce and the body's hash. The service rejects an unknown bank, a stale time (more than 2 min off), a replayed nonce or a bad MAC |
| Token service | `finmesh/services/apps.py` (`token_app`) | `POST /v1/evaluate`. The authenticated bank must be the query's bank (403 otherwise); over budget → 429; an invalid point → 400 |
| Bank node | `finmesh/services/apps.py` (`node_app`) | `POST /v1/evidence`. Requests carry the issuer's Ed25519 signature, which the node's own guard checks, so a refusal is the same `refused` message as in the harness. The node's clock (the replayed 6-hour window) is set only by orchestration, with an admin key, and never goes back |
| Clients | `finmesh/services/client.py` | `HttpTokenTransport` plugs into the harness's `TokenClient`; `HttpNode.respond` mirrors `BankNode.respond`. Service failures raise; they are never silent |
| Process entry point | `finmesh/services/run.py` | `uvicorn --factory finmesh.services.run:token_app_from_env`. Secrets come from the environment, never the command line |
| Tests | `tests/unit/test_week15.py` (11) | See below |

## What I ran here (results)

| Check | Result |
| --- | --- |
| Wire round trip | Every allowlisted message survives real JSON unchanged |
| Wire rejections | Wrong type, extra or missing field, float or bool as integer, S0 response, S1 response with a record, non-hex bytes, non-allowlisted object: all rejected |
| Authentication | Valid call accepted once; replay, stale time, wrong key, unknown bank, missing headers and a body changed after signing are all rejected |
| **Contract: tokens** | Tokens through HTTP equal the in-process tokens for the same seed |
| **Contract: evidence** | For S1, S2 and progressive disclosure, nine requests give **identical responses** through HTTP and in process, along with identical refusal counts, disclosures and inbound logs. The nine are normal, below the PD threshold, a second account, no record, an alert outside the range, a replay, a forgery, an unknown issuer and the wrong responder |
| Token service refusals | Over budget → `BudgetExceeded` at the client; no authentication → 401; a bank asking for another bank → 403; a replayed call → 401; an invalid point → 400 |
| Node clock | Wrong admin key → 401; a request expires by the node's own clock; the clock cannot go back; bad JSON and an undeclared purpose → 400 |
| **Separate process** | A real uvicorn process serves the token service. Tokens over real HTTP equal in-process tokens; once the process stops, the client fails loudly |
| CI mirror | All steps pass |

## Part 2: durable orchestration (2 Nov)

| Item | Where | Notes |
| --- | --- | --- |
| Session store | `finmesh/services/store.py` (`SessionStore`) | SQLite in WAL mode. Holds one session per alert, keyed by member, account and window; every planned request with its response; the card; and the analyst's actions. Each write is one transaction |
| Persistent token budgets | `BudgetLedger`, `token_app(..., ledger)` | Evaluations used per bank and epoch, and a log of every call, kept across restarts. The privacy ledger (week 16) reads it |
| Orchestrator | `finmesh/services/orchestrator.py` | The demo slice's online path, made durable: open, plan, request, fuse, card. The plan (every signed request) is stored before anything is sent |
| Four-eyes approval | `SessionStore.record_action` and `decide` | Escalating, freezing an account and filing a report wait for a second person; nobody approves their own action |

**How it behaves:**

- **A replayed alert never dispatches twice.** It finds its closed (or failed) session and gets it back unchanged.
- **After a crash, a restarted orchestrator resumes the session.** It never re-sends an answered request. A request that was in flight is re-sent with the *same* signature, so the node answers it at most once.
- **A member that stays unreachable** is recorded as `unavailable` after the retries. The case closes with partial evidence, flagged `evidence_incomplete` on the card.
- **If the token service is down or over budget before the plan is stored,** the session is retried, then ends `failed` after the maximum attempts. Every session ends `closed` or `failed`.
- **The card never names another member's account.**

**Tests (`tests/unit/test_week15_orchestrator.py`, 9), all passing:**

- Alert to card (2 members, 3 requests, peer alerts and records fused).
- A replayed alert sends no requests.
- A crash mid-session, then a restart on the same database: member 1's answered requests are not re-sent, and the crashed one is re-sent once.
- An unreachable member gives a flagged partial case after 1 try + 2 retries.
- A transient failure is retried successfully.
- The token service down ends `failed` after the maximum attempts; over budget also ends `failed`.
- No self-approval; already-decided actions can't be decided again.
- **Contract: the same alert through the HTTP services and in process gives an identical card.**
- The token budget survives a restart of the token service.

## Known limits, for week 16

- ~~The token service keeps its budgets in memory~~: fixed in part 2 (`BudgetLedger`).
- The nodes and the orchestrator are tested here with synthetic records. Week 16 loads real nodes from the frozen validation artifacts (the demo slice's setup), adds the analyst console (incident queue, evidence view, top-3 candidates and the A23 narrative, approvals) and the privacy ledger, which reads the session store, the budget ledger and the nodes' disclosures.
- The request issuer's signing key lives in the orchestration process. The proposal's threat model (ADV-5) bounds what it can sign; the key is not yet persisted, so a restarted issuer gets a new key and nodes must be given its public key. Week 16 fixes this when it wires the processes together.

## What you run on your machine

Nothing for week 15 part 1 beyond the usual check after `git pull`:

```bash
uv sync
bash scripts/ci_local.sh
```

`uv sync` installs the three new dependencies: FastAPI, uvicorn and httpx2 (the successor to httpx; switched on 2 Nov).
