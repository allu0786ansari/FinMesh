# Week 3 run log · 9 – 15 Nov 2026 · Evaluation harness

**Goal:** a harness that can score any detector at any budget, with test data locked away.

**State:** code complete; tested on the fixture, on a hand-built federation with known answers, and at HI-Medium scale (32 M synthetic rows). The real-data steps below also close Gate G0: re-running G0 under amendment A5 gives the HI-Medium count under B8.

## Gate G0 outcome (from your week-2 run)

Full note: `docs/gates/G0.md`. In short:

- **Decision: proceed, with the headline on HI-Medium and B8.** LI-Medium is the second regime; the Small sets become development data (amendments A5, A6).
- **One problem found, in my week-2 rule.** It projected test counts from train and validation together. Train schemes are almost never cut by a partition end, so the projection overstated sparse real-bank federations. On HI-Medium it chose A64, with a projection of 135 and an actual count of 87, where two thirds of every scheme is invisible to all members. B8 is now fixed by design; real-bank federations become a secondary partial-participation analysis. The A64 count was seen before the amendment, which is disclosed.
- **Grounding (H3b) as written would be trivially true.** Your probe gave 100% grounding for both models because the schema's candidate list forces it. H3b is now measured with JSON-only decoding (amendment A7); the `--free` probe in step 6 gives the first number.
- **Local model: llama3.2:3b**, p95 23 s. Latency target p95 ≤ 30 s; narratives evaluated on a sample of 200 incidents.

## What was built

| Item | Where | Notes |
| --- | --- | --- |
| Account-window labels | `finmesh/eval/universe.py` | Every active account-window per member and partition: positive, masked or negative. Built in hash slices. Test written to `data/sealed/` |
| Frozen split plan | `docs/protocol/split_plan_<ds>.json` | Written by `finmesh labels`; a real-data test fails if a local plan ever differs |
| Sealed test entry point | `finmesh/eval/sealed.py` | `EvalStore` refuses test; `open_sealed_test` logs to `data/sealed/<ds>/access_log.jsonl` before returning data and refuses a second opening per config and seed (CC2) |
| Label guard | `finmesh/eval/guard.py`, `tests/contract/test_label_guard.py` | `FeatureFrame` and `ScoreFrame` refuse label columns; a static check parses every module in features, models, sharing, matching and fusion for label names (CC1) |
| Metrics | `finmesh/eval/metrics.py` | AUPRC, AUROC (ties as one threshold, weighted), precision at k |
| Alert budgets | `finmesh/eval/budgets.py` | Per member: FPR 0.1% and 0.01% (fitted on an earlier partition, deterministic tie-breaking), and 1 alert per 1,000 accounts per day (top-k per window) |
| Scheme metrics | `finmesh/eval/schemes.py` | Detected, time to detect, linked and linked across members (incident table), allowed delay; exact random-alert baseline |
| Statistics | `finmesh/eval/stats.py`, `RankedScores.bootstrap` | Cluster bootstrap over schemes (seed-averaged) and over accounts (Poisson weights), paired bootstrap with p-value, Holm |
| Harness | `finmesh/eval/harness.py` | `evaluate` is the single entry point every experiment will use; `harness_check` runs two label-free reference scorers |
| CLI | `finmesh labels`, `harness-check`, `sealed-log` | |
| Fixes from your G0 run | `finmesh/eval/g0.py`, `cli.py`, `profile.py` | A5 rule; summary covers every dataset (your Medium run had overwritten the Small summary); profile now reports real memory, not memory-mapped file pages |

### Definitions fixed this week

- **Evaluation unit:** account-window = an account held at a member, in one 6 h window, with at least one transaction. Inactive accounts are never scored, as in a bank's monitoring.
- **Label:** positive if it touches an unmasked laundering transaction; masked if it touches only legs of schemes assigned to another partition; else negative. Masked windows count in neither precision nor recall, but alerts on them still use budget.
- **Detected scheme:** at least one of its account-windows in its own partition is alerted within the delay.
- **Linked scheme:** two or more of its accounts fall into one incident, and across members when those accounts sit at different members. Linked detection is 0 until fusion produces incidents (week 7); the harness already takes an incident table.
- **Random-alert baseline:** computed exactly. A scheme with account-windows at members alerting at rates p is detected with probability 1 − Π(1 − p).
- **Budgets:** fitted on the earlier partition (train for validation, validation for test). Ties at the threshold are broken by a fixed hash of (account, window), so integer-valued scorers use exactly their budget.

## What I ran here (results)

| Check | Result |
| --- | --- |
| CI mirror (`bash scripts/ci_local.sh`) | All steps pass |
| Unit and contract tests | All pass; coverage above 80% |
| Metrics against known answers | AP on a hand example (0.8333); AUROC equal to brute-force Mann-Whitney with ties; weights equal duplication; fast AP equal to an independent reference with ties and weights |
| Hand-built federation | Detection, time to detect, delay, linked within and across members, exact random-detection probabilities all as computed by hand |
| Labels against a naive recomputation | Identical on the fixture, with 1 slice and with more than 5 slices |
| Sealed test | Refuses test outside the entry point; logs every opening; refuses a repeat; logs a deliberate repeat |

At HI-Medium scale (32 M synthetic rows, 8 members, 30.6 M training and 11.1 M validation account-windows, more accounts than the real data, so pessimistic):

| Step | Time | Peak memory |
| --- | --- | --- |
| `labels` | 111 s | 1.3 GB |
| `harness-check` (2 scorers, 1,000 scheme and 200 window replicates) | 163 s | 2.4 GB |

| Scorer (synthetic data, no signal by construction) | Prevalence | AUPRC [95% CI] | AUROC | Realised FPR at 0.1% / 0.01% |
| --- | --- | --- | --- | --- |
| random | 0.001164 | 0.001158 [0.001132, 0.001183] | 0.4995 | 0.00099 / 0.000097 |

The random scorer sits on its baseline, and the budgets are met per member. Getting there needed three performance fixes, all exact (same numbers, cheaper):

- Scores now attach to labels by row order when keys match (a 30 M-row hash join had exhausted memory).
- AUPRC and AUROC are computed only at groups holding positives, which made the bootstrap 3.5 times faster.
- Thresholds use a per-member top-k instead of a full sort (peak 4.3 → 1.9 GB).

## What you run on your machine

About 30 minutes, most of it the Medium datasets.

### 1. Update and check (2 min)

```bash
cd ~/FinMesh
git pull
uv sync
bash scripts/ci_local.sh
```

Expected: `local CI: all steps passed`.

### 2. Re-run G0 with amendment A5 (6–8 min)

```bash
uv run finmesh g0 --dataset HI-Small --dataset LI-Small --dataset HI-Medium --dataset LI-Medium
```

Every dataset now counts test schemes under B8. Expected: HI-Small 73, LI-Small 18, LI-Medium 91 (unchanged), and **HI-Medium under B8 about 450–550** (proceed band). `docs/gates/G0_evidence_summary.md` now covers all four datasets.

### 3. Build the account-window labels (8–12 min)

```bash
uv run finmesh labels --dataset HI-Small
uv run finmesh labels --dataset LI-Small
uv run finmesh labels --dataset HI-Medium
uv run finmesh labels --dataset LI-Medium
```

Each prints train and validation counts (test stays sealed) and freezes the split plan into `docs/protocol/`.

### 4. Harness check (6–10 min)

```bash
uv run finmesh harness-check --dataset HI-Medium
uv run finmesh harness-check --dataset LI-Medium
uv run finmesh harness-check --dataset HI-Small
```

Writes `docs/eval/harness_check_<ds>.md`. **What to look for:** for the `random` scorer, AUPRC within a few percent of the prevalence, AUROC within about 0.01 of 0.5, the realised FPR at most the budget, and "Detected" inside the random-alert interval. If any of these fails on real data, stop and send me the page.

### 5. Confirm the seal (seconds)

```bash
uv run finmesh sealed-log --dataset HI-Medium
```

Expected: `the sealed test has never been opened`.

### 6. Unconstrained language-model probe (about 8 min)

```bash
uv run finmesh llm-probe --model llama3.2:3b --free --save
```

Writes `docs/gates/llm_probe_llama3.2_3b_free.json`: grounding without the schema forcing it (amendment A7).

### 7. Real-data tests and push

```bash
uv run pytest -m real_data -v
git add docs/gates/ docs/protocol/ docs/eval/
git commit -m "Week 3: G0 under A5, labels, harness check on real data"
git push
```

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `membership_B8.parquet missing` | Step 2 not run for that dataset | Run step 2 |
| `labels not built` in harness-check | Step 3 skipped | Run step 3 |
| `Killed` | WSL memory cap | `.wslconfig` `memory=6GB` (week-2 run log, step 2) |
| Random scorer far from baseline | Harness or label bug | Stop; send the harness page |
| `SealedTestError` | Something requested the test partition outside the entry point | Expected behaviour; nothing in week 3 should open test |

## Week-3 checklist against the plan

- [x] Freeze the split code; windows generated after splitting (plans committed in step 3)
- [x] Sealed-test entry point with logged access
- [x] Label guard: separate label type, refusing constructors, static check (CC1)
- [x] Metrics: AUROC, AUPRC, precision at k, false alerts per 1,000 accounts per day, any-alert and linked scheme detection, time to detect
- [x] Per-member alert budgets (0.1%, 0.01% FPR; 1 per 1,000 accounts per day), fitted on an earlier partition only
- [x] Random-alert baseline (exact)
- [x] Cluster bootstrap over schemes, paired bootstrap, Holm correction
- [x] Provenance stamp on every artifact; fixture artifacts refused at gates (CC3)
- [x] Done when: every metric passes unit tests on a hand-built federation with known answers

## Open items for you

1. Run steps 1–7 and push.
2. Still open from week 1: code licence (Apache-2.0 or MIT) and the dataset licence in `docs/data_card.md`.
