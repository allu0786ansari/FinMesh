# Week 10 run log · 28 Dec 2026 – 3 Jan 2027 · Gate G2 decision; neural scorer, DP-SGD and FedAvg

**Goal:**
- close Gate G2;
- start the federated DP track (RQ2): the neural scorer, a DP-SGD engine with persistent accounting, FedAvg, and the first X4 comparison on validation.

**State:**
- G2 is passed and written up.
- The neural track is code complete and tested: a gradient check, exact per-unit clipping, noise scale, accountant calibration, the budget guard and persistence, and an end-to-end DP learning test.
- It has been run on the fixture and at stress scale.
- Your run gives the first real RQ2 numbers.

## Week-9 review and Gate G2 (your run, pushed 29 Oct)

Complete and consistent; G2 evidence in `docs/gates/G2_evidence.md`, decision in **`docs/gates/G2.md`**.

| | HI-Medium | LI-Medium |
| --- | --- | --- |
| H1a: S2 − S0 linked detection | +0.56 [0.52, 0.60] | +0.54 [0.45, 0.64] |
| H1b: S2 share of the relational oracle's gain | 0.98 [0.94, 1.02] | 0.83 [0.74, 0.92] (0.78 against the stronger pooled one) |
| H1c: S1 and S3 (ε ≤ 2) within 0.05 | no (pass-through, rare target) | no (S1's flags leak fan-in) |
| PT2: OPRF vs hashing at the sized budget | 11.0× | 7.8× |
| A4: S3 linkable after rotation | at chance at every ε (S2: 0.54) | at chance (S2: 0.46) |
| A5: S4 reveals autoencoder training rows | no (AUC 0.50) | no (AUC 0.50) |
| A6: TPR gain from being asked | +0.075 | +0.024 |
| Demo slice p95 (PT6 ≤ 3 s) | 0.023 s | 0.011 s |

**Decision: G2 passed.** The headline study is complete on validation and frozen for test. The note:
- explains both H1c failures (neither is a defect);
- recommends no further amendment;
- lists everything frozen for week 18.

Please read `docs/gates/G2.md`. If you disagree with "no further amendment" for H1c, say so now; after this week it would be too close to test.

The A16 fix did what it should: S3's leakage now equals S1's (LI fan-in AUC 0.72 for both, 0.89 before), and A4 cannot link S3 records across a rotation.

## Amendment A17 (your tool choice; specification fixed before any neural result)

- **Tools.** DP-SGD in NumPy, Google's `dp-accounting` RDP accountant, and FedAvg in process; no PyTorch, Opacus or Flower. Their CPU index is blocked here, so that stack could not be tested before pushing. The NumPy engine is small enough to verify exactly.
- **Encoding.** Fixed piecewise-linear bins per feature kind (counts, amounts, shares, hours, rates, log-differences) plus a missing indicator. Nothing is estimated from any bank's data, so normalisation costs no privacy (CC4).
- **Network.** MLP 64-32-1, ReLU, no batch normalisation; weight 10 on positives.
- **Training.**
  - Rows: the GBDT's training rows.
  - Optimiser: Adam at lr 1e-3, batch 512 per client step.
  - Schedule: 50 rounds × 20 local steps.
  - DP-SGD: clip norm 1.
  - Nothing is tuned on validation.
- **Privacy.**
  - Window unit this week; ε ∈ {1, 3, 10}; δ = 0.1 / N per client.
  - The noise is calibrated once for 1,000 steps.
  - Accountants persist per run, and a budget guard stops any step beyond the plan.
  - Every private training is appended to `data/artifacts/week10/privacy_ledger_<ds>.jsonl`, which is never rewritten.
- **H2a.** FedAvg + DP at ε ≤ 10 reaches at least 0.70 of the centralised MLP's AUPRC and beats the local-only MLP.

## What was built

| Item | Where | Notes |
| --- | --- | --- |
| Neural scorer | `finmesh/models/neural.py` | Fixed piecewise-linear encoding; MLP; forward and backward pass; exact per-unit gradient norms from k×k Gram matrices (window unit: one row per unit; account unit: a bag of rows) |
| DP-SGD client | `finmesh/federation/dpsgd.py` | Poisson sampling of units; exact clipping; Gaussian noise σC; fixed denominator qN; Adam as post-processing; non-private step for the references |
| Accountant | `finmesh/federation/accountant.py` | `dp-accounting` RDP; noise calibration by bisection; persistent state; budget guard (`BudgetExceeded`) |
| FedAvg | `finmesh/federation/fedavg.py` | Equal weights, all members every round, client optimiser state stays on the client, accountants saved every round |
| X4 part 1 | `finmesh/training/x4.py`, `finmesh x4` | Centralised, local-only, FedAvg, and FedAvg + DP (ε 1, 3, 10) MLPs; the local GBDT as reference; paired account bootstrap; H2a; privacy ledger |
| Tests | `tests/unit/test_dp.py`, `tests/integration/test_real_data_week10.py` | |

### Design choices to review

- **Every unit is clipped** (at C = 1, about 100% on the fixture, 3% on the synthetic check). Clipping then acts like gradient normalisation, which is common in DP-SGD. C stays fixed rather than tuned on validation; if the real run shows the DP models far below the non-private ones, C and the learning rate are the first suspects, and we would tune them on the training hold-out, not validation.
- **FedAvg weights clients equally.** Client sizes are not used, so they are not disclosed. B8's members are balanced by accounts, so the two weightings differ little.
- **One privacy unit this week.** The account unit (one account's bag of at most k windows) and the degree cap come in week 11. The engine already handles bags; only the data grouping and the cap are left.

## What I ran here (results)

| Check | Result |
| --- | --- |
| Gradient | Matches finite differences on every layer |
| Per-unit norms | Equal to explicit per-unit gradients for window units and for account bags; every clipped unit is within C |
| DP noise | Standard deviation σC / (qN) as specified |
| Accountant | Calibrated ε at most the target and within 3% of it; resumes after reload; refuses the step after the last planned one |
| DP learns | Synthetic, 4 clients × 100,000 units, 1% positives: AUPRC 0.99 non-private, 0.98 at ε = 10, 0.97 at ε = 3, 0.87 at ε = 1; about 10 s per configuration |
| CI mirror | All steps pass, including `finmesh x4` on the fixture |

At stress scale (SCALE-Tail, one seed):

| Measure | Value |
| --- | --- |
| One seed, all configurations | 775 s (13 min), peak 2.3 GB |
| Training per configuration | Centralised, local and FedAvg about 38 s each; FedAvg + DP about 57 s each (8 clients × 1,000 steps) |
| Clients | 8 × about 110,000 training units (window unit) |
| DP at ε = 1 | Noise multiplier 1.17, sampling rate 0.0047, δ 9.1e-7; about 2% of sampled units clipped |
| Scoring validation (all configurations and the GBDT) | 336 s, down from 630 s once all models scored in one pass over the validation slices |

The stress set's labels are random, so its AUPRCs (about 0.003) mean nothing; only time, memory and the accounting carry over.

## What you run on your machine

About 1 hour of machine time.

### 1. Update and check (5 min)

```bash
cd ~/FinMesh
git pull
uv sync                     # adds dp-accounting
bash scripts/ci_local.sh
```

### 2. Read the G2 note

Read `docs/gates/G2.md`. Tell me if you disagree with any decision in it.

### 3. Run X4 part 1 (about 30–40 min per dataset)

```bash
uv run finmesh x4 --dataset HI-Medium
uv run finmesh x4 --dataset LI-Medium
```

It writes `docs/eval/x4_<ds>.md` and appends to the privacy ledger in `data/artifacts/week10/`.

**What to look for:**

- **The MLP against the GBDT.** The proposal expects the GBDT to stay stronger (risk register: "neural scorer underperforms the GBDT"); that would be a finding, not a failure.
- **H2a:** FedAvg + DP at ε = 10 and ε = 3 against 0.70 of the centralised MLP.
- **Share clipped and the noise multipliers** in the accounting table. If almost every unit is clipped and DP AUPRC collapses even at ε = 10, tell me before week 11.

### 4. Tests and push

```bash
uv run pytest -m real_data -v
git add docs/eval/ docs/gates/
git commit -m "Week 10: X4 part 1 on real data"
git push
```

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `No module named 'dp_accounting'` | `uv sync` not run | `uv sync` |
| `BudgetExceeded` | A run reused an accountant directory | Each run gets a new directory by timestamp; do not copy accountant files between runs |
| `... holds a different plan` | An accountant file from a different plan | Same: start a new run |

## Week-10 checklist against the plan

- [x] Gate G2 evidence reviewed, decision note written
- [x] Neural scorer without batch normalisation, with numerical embeddings (fixed piecewise-linear)
- [x] DP-SGD with exact per-unit clipping, Poisson sampling, persistent RDP accounting, budget guard, privacy ledger
- [x] FedAvg (in process)
- [x] X4 part 1: centralised, local-only, FedAvg, FedAvg + DP at ε ∈ {1, 3, 10}, GBDT reference
- [ ] Done when: X4 part 1 on HI- and LI-Medium validation (your step 3)
- Week 11: the account unit, the degree cap and the indirect-influence measurement (X5 setup)
