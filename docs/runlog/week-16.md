# Week 16 run log · 8 – 14 Feb 2027 · Analyst console and privacy ledger on real data

**Goal (proposal section 13):** an analyst console and a privacy ledger on the demo path:
- **Console:** an incident queue cut at the bank's budget; a cross-bank evidence view showing which sharing level each response used; the attribution and summary; approve and reject controls for high-impact actions.
- **Privacy ledger:** model ε per bank, evidence disclosure, OPRF queries against budget, and every evidence request and response.

**State (2 Nov):** code complete and tested here: unit cases, and the whole real-data path at fixture scale. On your machine it is three commands and about 20–40 minutes, plus a look at the console in your browser.

## What was built

| Item | Where | Notes |
| --- | --- | --- |
| Demo world | `finmesh/services/world.py`, `finmesh demo-build` | Reuses the demo slice's setup without changing it: each member's local detector and calibration, primary-budget alerts, S2 evidence records, and alerts with counterparties at other members. Saved under `data/demo/<dataset>/`; secrets go in `secrets.json`, mode 0600 and never committed |
| Serving it | `run_world`, `finmesh demo-run` | The token service (with its persistent budget ledger) and one node per member as HTTP apps, plus one orchestrator per member. Every message crosses the wire format and every check. Orchestration advances the nodes' clocks; time never goes back |
| Signing key kept | `new_issuer_key`, `issuer_from` in `finmesh/services/world.py` | A restarted demo signs with the same key, so the nodes keep trusting it (the week-15 limit). Key handling lives on the orchestration side: the key-isolation contract test (CC5) caught a first version that put it in the bank-side `requests.py` |
| Case summary | `finmesh/services/enrich.py` | The bank's own view, worded with the A23 readings, so it passes the A23 claim check. A **typology hint** from the catalogue rules, labelled as a hint: the evaluated attributor is X6. Review actions come from the catalogue. No language model runs on the demo path |
| Privacy ledger | `finmesh/services/ledger.py` | **Model:** no shared model (Gate G3 kept detectors local), so no model ε. **Evidence:** per member, requests sent and received, records released, alert flags revealed, refusals and unreachable cases; S2 records are minimised but not differentially private, so disclosures are counted, not ε. **Tokens:** OPRF evaluations per bank and epoch against the budget. **Audit:** every request |
| Console | `finmesh/services/console.py`, `finmesh console` | One local page (127.0.0.1 only): incident queue ranked by fused score with the budget cut marked; case view (card, evidence by member with level and status, hint, summary, review actions); actions with four-eyes approval; privacy-ledger tab. Light and dark theme |
| Tests | `tests/unit/test_week16.py` (5) | See below |

## What I ran here (results)

| Check | Result |
| --- | --- |
| Signing key | Export and reload: requests from the reloaded signer pass the guard that trusts the original key |
| Case summary | Uses the readings ("12 (many payees)", "0.00 (none passed on)"); passes the A23 claim check; the hint and actions come from the catalogue |
| Privacy ledger | Counts every request, record released, alert flag and "no record" per member; names no account or token |
| Console API | The queue is ranked; unknown session → 404; unknown action → 400; empty analyst name → 422; escalation waits for approval; self-approval → 403; deciding twice → 409; the ledger is served |
| **Real-data path at fixture scale** | `build_world` → 6 alerts with counterparties, secrets file mode 0600. `run_world` → **6 of 6 sessions closed**. Running again sends nothing new. The ledger shows the OPRF calls with no refusals, and the console serves the queue and cards |
| CI mirror | All steps pass |

**Found while building the summary:** the frozen A23 claim check does not see negation for cycles. All 7 HI cycle flags (3 of 4 on LI) were correct "no cycles" sentences. This is noted in the week-14 run log, and the console's summary avoids the word.

## What you run on your machine

### 1. Update and check (about 15 min)

```bash
cd ~/FinMesh
git pull
uv sync
bash scripts/ci_local.sh
```

### 2. Build and run the demo world (about 20–40 min)

```bash
uv run finmesh demo-build --dataset HI-Medium --alerts 200
uv run finmesh demo-run --dataset HI-Medium
```

`demo-build` fits each member's detector on HI-Medium, as the week-9 demo slice did, and samples 200 alerts that have counterparties at other members. `demo-run` sends each alert through the services. It prints the closed and failed counts and the latency per alert against PT6 (3 s).

### 3. Open the console

```bash
uv run finmesh console --dataset HI-Medium
```

Open `http://127.0.0.1:8050` in your browser:
1. Type your name in **Analyst**.
2. Click an incident: check the evidence table (which members answered, at which level, with or without a record), the summary and the hint.
3. Record an `add_note`, then an `escalate`.
4. Try to approve the escalation under your own name; it must refuse. Change the name to approve it.
5. Open **Privacy ledger**.

Take two or three screenshots for the report and slides. Stop the console with Ctrl+C.

### 4. Push

```bash
git add docs/ && git commit -m "Week 16: demo world run and console check" && git push
```

The demo world itself stays in `data/` and is not committed. Please paste the `demo-run` output (states and latency) into your message, or into this run log.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `demo-build` reports 0 alerts | The alert budget gives no alerts with cross-member counterparties | Use a larger dataset or more `--alerts`; on HI-Medium this should not happen |
| `no demo world` | `demo-build` not run | Run it first |
| Port 8050 in use | Another program | `--port 8060` |
| Out of memory in `demo-build` | It fits all members' detectors, like the week-9 slice | Close other programs |

## Week-16 checklist against the plan

- [x] Real-data nodes and orchestration; persistent signing key
- [x] Analyst console: queue, evidence view, hint and summary, approvals
- [x] Privacy ledger: model, evidence, tokens, audit
- [ ] Your run on HI-Medium and the console check
- Week 17: X7 (end-to-end latency, fault and chaos tests, resource benchmark) and the container packaging
