# Week 15 run log · 1 – 7 Feb 2027 · Demo path, part 1: services and the contract test

**Goal (proposal weeks 15–17):**
- Weeks 15–17 build the demo path, the analyst console, the privacy ledger and X7.
- **Week 15** builds the demo path's transport: the token service and the bank nodes as separate HTTP processes. They exchange only the allowlisted messages, and a contract test shows they emit exactly the same messages as the research harness for the same inputs (engineering acceptance).

**State (2 Nov):** part 1 done here and tested; it needs nothing from your machine. Part 2 comes next: orchestration with durable sessions and idempotency, then the analyst console and privacy ledger (week 16), then X7 (week 17). The A23 narrative runs overnight on your machine in parallel; its frozen output feeds the console's incident card.

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

## Known limits, for part 2

- The token service keeps its per-bank budgets in memory, so a restart resets them. Part 2 persists the budget ledger, and the privacy ledger reads it.
- Nodes are built in-process here. Part 2 adds the node process with its evidence store loaded from the frozen artifacts, plus the orchestrator: sessions in SQLite, an idempotency key per alert, and signed requests.

## What you run on your machine

Nothing for week 15 part 1 beyond the usual check after `git pull`:

```bash
uv sync
bash scripts/ci_local.sh
```

`uv sync` installs the three new dependencies: FastAPI, uvicorn and httpx.
