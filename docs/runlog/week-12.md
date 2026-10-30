# Week 12 run log · 11 – 17 Jan 2027 · DP retune, IID arm, membership audit, stacked ensemble, Gate G3

**Goal:**
- fix the two flaws of the A18 tuning grid, on proxy data only (A19);
- finish X5 with the bank-partitioned vs IID arm;
- audit the federated model with membership inference;
- stack the federated scorer with each bank's own detectors (X4 part 2);
- gather the Gate G3 evidence and apply the rule fixed in A19.

**State:** code complete and tested (unit cases, fixture pipelines, stress scale). One script runs every real-data step unattended: `bash scripts/week12.sh`.

## Week-11 review (your run, pushed 30 Oct)

### 1. A18 tuning chose the A17 defaults, and the grid could not have shown better

| Proxy | Chosen | Hold-out AUPRC (ε = 3) | Trend in the grid |
| --- | --- | --- | --- |
| HI-Small | clip 1, batch 512 | 0.416 | AUPRC rises with every clip step up to 1, the grid's largest |
| LI-Small | clip 1, batch 512 | 0.151 | Same |

Two flaws in my grid design, both now fixed in A19:

- **The best clip norm was at the grid's edge.**
  - A small clip norm cuts every gradient to the same size.
  - Laundering rows carry weight 10 and large gradients; easy legitimate rows have tiny ones.
  - So a small clip shrinks exactly the rows that carry the signal, which cancels the class weighting. The data say the optimum is at clip 1 or above.
- **Batch size was confounded with training length.**
  - A18 held the number of *examples* fixed with a fixed learning rate.
  - Batch 8,192 therefore got 50 updates against 1,000 for batch 512, and was simply undertrained. Its higher share of clipped units is consistent with a model further from convergence.
  - The comparison never tested whether a larger batch, which divides the same noise over more rows, helps.

### 2. X5 with the A18 settings (identical to week 10's for the window unit)

| Validation AUPRC, ε = 10 | HI-Medium | LI-Medium |
| --- | --- | --- |
| Centralised MLP, non-private | 0.310 | 0.087 |
| Local-only MLP, non-private | 0.252 | 0.061 |
| Window unit | 0.153 | 0.033 |
| Account unit | 0.171 | 0.034 |
| Account unit, capped | **0.184** | 0.034 |
| H2a share (window) | 0.49 [0.47, 0.52] | 0.38 [0.35, 0.42] |

- **H2a fails** on both datasets at every ε, and DP is below the local-only network everywhere.
- **H2b is not supported.**
  - HI-Medium: window − account is +0.014 [0.011, 0.017] at ε = 1, about 0 at ε = 3, and −0.018 [−0.021, −0.015] at ε = 10.
  - LI-Medium: the account unit is slightly better at every ε (about 1.03×).
  - Why: an account's bag of up to 8 windows is clipped once, and with a clip norm that binds only about 3% of the time, the bag carries several windows of gradient for one unit of noise. The stronger unit costs nothing here; each step also sees more rows. This is a finding for the paper, stated with that caveat.

### 3. Influence: the degree cap is the week's main result

| Group size (other same-member training accounts one account moves) | HI uncapped | HI capped | LI uncapped | LI capped |
| --- | --- | --- | --- | --- |
| Median | 2 | 2 | 2 | 2 |
| p90 | 267 | 5 | 2,234 | 4 |
| p99 | 3,463 | 9 | 3,633 | 7 |
| Max | 3,750 | 11 | 3,643 | 9 |
| Accounts changed by 200 removals | 33,632 | 794 | 44,430 | 706 |

- Without the cap, the account-unit guarantee says little for hub-adjacent accounts: one account's removal changes the features of thousands of others.
- With D = 16 the worst case is about 10 accounts, so a group bound is meaningful at small ε.

### 4. The cap costs almost nothing

| | HI-Medium | LI-Medium |
| --- | --- | --- |
| Non-private, capped − uncapped | −0.020 [−0.024, −0.015] | +0.001 [−0.001, 0.002] |
| Account unit under DP, capped − uncapped (ε 1 / 3 / 10) | +0.004 / +0.012 / +0.013, all CIs above 0 | about 0 |

Under DP the cap *helps* on HI-Medium. A likely reason: capped features have lighter tails, so fewer gradients are cut by clipping. This is not tested separately.

### Your decisions (30 Oct)

- **Retune inside week 12** on the proxy federations, with the flaws fixed (A19).
- **Deployed setup = account unit + degree cap 16** for membership inference, the ensemble and G3. H2a stays judged as pre-registered (window unit, uncapped).

## Amendment A19 (pre-registered and pushed before any week-12 code: commit `9997684`)

- **Retune grid** (proxy only, one retune):
  - clip ∈ {1, 3, 10} × expected batch ∈ {512, 2048} × lr ∈ {1e-3, 3e-3, 1e-2};
  - every setting 50 rounds × 20 local steps, so every setting takes the same 1,000 updates and a larger batch costs proportionally more compute;
  - ε = 3, window unit, seed 0, scored on HI-Small / LI-Small hold-outs;
  - ties go to the cheaper setting; a winner on the grid's edge is reported, not extended;
  - a non-private FedAvg is scored on the same hold-out for context.
- **X5 IID arm:** deployed setup; the same training accounts dealt to clients at random, keeping each client's number of accounts; non-private FedAvg and DP at ε ∈ {1, 3, 10}, seeds 0–2, paired against the bank-partitioned arm.
- **A5 on the model:** each member's training accounts split 50/50 by a fixed hash into IN and OUT; models trained on IN only. The attacker, a peer bank holding the global model and (worst case) the candidate account's rows and labels, scores each candidate by:
  - LOSS, the bag's mean weighted loss;
  - REF, its own local model's loss minus the global model's.
  - The audit fails if a DP model's TPR at 1% FPR has a lower 95% bound above e^ε × 0.01 + δ.
- **Stacked ensemble:** the A13 stacker on logit(GBDT), log(autoencoder error) and logit(neural), per member, cross-fitted on the validation halves. The primary comparison is local ensemble + DP scorer − local ensemble.
- **G3 rule:**
  - **Blocked** if any client overspent ε or the audit fails.
  - **Otherwise** the DP scorer joins the deployed detector at the smallest ε ≤ 10 whose ensemble gain on HI-Medium has a CI above 0.
  - **If none does,** the local ensemble is deployed and the DP scorer is reported as a finding.

## What was built

| Item | Where | Notes |
| --- | --- | --- |
| A19 grid | `finmesh/training/dp_tune.py`, `finmesh dp-tune --grid A19` (default) | 18 settings at equal updates; non-private reference; edge flags; A18's choice kept under `history` in `dp_hparams.json`; report `dp_tune_<ds>_A19.md` |
| X5 IID arm, saved models | `finmesh/training/x5.py` (`iid_partition`, `save_models`), `finmesh x5` | Writes to `week12`; report `x5_<ds>_A19.md` (the A18 page stays); `--no-iid` skips the arm (proposal cut order) |
| Membership audit | `finmesh/training/membership.py`, `finmesh membership` | IN/OUT by fixed hash; LOSS and REF; AUC, TPR at 1% and 0.1% FPR with account bootstrap; DP bound check; Clopper–Pearson ε lower bound; ledger entries |
| Stacked ensemble | `finmesh/training/ensemble.py`, `finmesh ensemble` | Loads X5's saved models; refits the GBDT and autoencoder per seed; gains over the local ensemble |
| Gate G3 | `finmesh/eval/g3.py`, `finmesh g3` | Evidence page `docs/gates/G3_evidence.md`; ledger check over weeks 10–12; applies the A19 rule |
| One-shot runner | `scripts/week12.sh` | Every step in order; resumable (skips steps whose artifact exists) |
| Tests | `tests/unit/test_week12.py`, `tests/integration/test_real_data_week12.py` | |

### Design choices to review

- **Tuning stays on the window unit.** H2a is judged on it, and A18 tuned on it; one setting serves both units, as before. The account unit at the same expected batch sees up to 8× more rows per step, so if anything it is favoured.
- **The membership attacker is deliberately strong.** It knows the candidate's rows and labels, as in DP auditing, so a pass is meaningful. The IN/OUT split is random over the same accounts, so the only difference between IN and OUT is training membership.
- **REF's reference model is the attacker's own local network**, trained only on its own customers. That is realistic: a peer bank has exactly that data.
- **The ensemble refits the GBDT and the autoencoder per seed** rather than reading old scores, so every input of a seed shares its negative sample.

## What I ran here (results)

| Check | Result |
| --- | --- |
| A19 grid | 18 settings, all at 20 local steps; A18 still reproducible with `--grid A18` |
| Tie-breaking | Equal AUPRC goes to the smaller batch, then clip, then lr |
| Retune history | The A18 entry moves to `history`; the Medium sets read the new one |
| IID partition | Client sizes in accounts kept exactly; an account's rows move together; fixed by seed; no copy of the features |
| Saved models | Round trip exact |
| TPR at FPR | Never above the target FPR (ties included); useless scores give TPR ≈ FPR |
| Empirical ε | 0 when TPR ≤ FPR; conservative for a strong attack |
| G3 rule | joins / local ensemble / blocked (audit) / blocked (accounting) all exercised |
| Fixture pipelines | X5 with IID, membership, ensemble, g3; every client's spent ε within target |
| CI mirror | All steps pass |

At stress scale (SCALE-Tail, 32 M rows, worst-case A19 setting: clip 3, batch 2048, lr 3e-3):

| Step (one seed) | Time | Peak memory | Notes |
| --- | --- | --- | --- |
| X5, all 26 trainings + scoring | 1 h 54 min | 3.4 GB | Inflated: local CI shared the 2 cores for most of it, and the last scoring step was paused while I pushed the fix |
| One DP training, window unit | about 3 min | | 4× the batch-512 cost, as expected |
| One DP training, account unit | about 6 min | | Bags carry up to 8 rows per unit |
| Non-private FedAvg / centralised | about 40 s | | |
| Scoring all models, one view | 7–18 min | | |
| Membership audit (4 trainings on IN, 8 references, 706,210 candidate accounts) | 22 min | 2.3 GB | IN 352,351 / OUT 353,859: balanced. Attack AUC 0.50 for every model: this synthetic data has random labels, so there is nothing to leak; only time and memory are measured |
| Ensemble (GBDT, autoencoder, scoring, stacking) | about 6 min before the bootstrap | | The run was cut by a container restart during the final bootstrap (1–2 min). Real-data GBDT fits take longer than on this signal-free data |

The IID arm behaves as it should on signal-free data: IID − partitioned is 0 within ±0.00003 at every ε.

## What you run on your machine

Machine time depends on the batch size the retune picks. Run it overnight:

| Step | Batch 512 chosen | Batch 2048 chosen |
| --- | --- | --- |
| A19 tuning, per proxy (18 settings; half are batch 2048 either way) | about 40 min | about 40 min |
| X5, per dataset (3 seeds) | about 2–2.5 h | about 4–5.5 h |
| Membership audit, per dataset | about 10 min | about 25 min |
| Ensemble, per dataset (3 seeds) | about 25 min | about 25 min |
| **Total, both datasets** | **about 7 h** | **about 12 h** |

Peak memory stays under 3.5 GB.

### 1. Update and check (5 min)

```bash
cd ~/FinMesh
git pull
uv sync
bash scripts/ci_local.sh
```

### 2. Run everything (unattended)

```bash
bash scripts/week12.sh 2>&1 | tee week12.log
```

It runs, in order:

1. `dp-tune --grid A19` on HI-Small and LI-Small. This writes `finmesh/schemas/dp_hparams.json` and `docs/eval/dp_tune_<ds>_A19.md`.
2. `x5` on HI-Medium and LI-Medium → `docs/eval/x5_<ds>_A19.md`.
3. `membership` on both → `docs/eval/membership_<ds>.md`.
4. `ensemble` on both → `docs/eval/ensemble_<ds>.md`.
5. `g3` → `docs/gates/G3_evidence.md`, then `pytest -m real_data`.

If it stops (power, sleep), run the same command again: finished steps are skipped.

**What to look for in the log:**

- **The A19 choice** (`chosen: clip …, batch …, lr …`) and whether it sits on the grid's edge.
- **H2a with retuned DP:** the window unit at ε = 10 against 0.70 of the centralised MLP.
- **IID − partitioned:** how much the banks' different populations cost.
- **`audit violation: False`** for the membership audit, and the non-private model's REF AUC (attack power).
- **`smallest qualifying eps`** from the ensemble on HI-Medium: this decides G3.

### 3. Push

```bash
git add docs/eval/ docs/gates/G3_evidence.md finmesh/schemas/dp_hparams.json week12.log
git commit -m "Week 12: A19 retune, X5 with IID arm, membership audit, ensemble, G3 evidence"
git push
```

Please include `week12.log`: the timings and the per-setting tuning lines are in it. I write the G3 decision note (`docs/gates/G3.md`) from what you push.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `no tuned DP settings for this regime` | Step 1 did not finish | Re-run `scripts/week12.sh` |
| `no week-12 X5 run for …; run finmesh x5 first` | The ensemble ran before X5 | Re-run the script; it does X5 first |
| `this X5 run saved no models` | An X5 artifact from before this week | Delete `data/artifacts/week12/x5_<ds>.json` and re-run |
| `features_..._cap16_v3/meta.json missing` | Capped features from week 11 deleted | `uv run finmesh features --dataset <ds> --degree-cap 16` |
| `BudgetExceeded: client 0: 1001 steps planned for 1000` in `dp-tune` | Fixed 30 Oct (`git pull`): settings differing only in learning rate shared one accountant folder, so the guard refused to spend privacy twice | `git pull`, then re-run `scripts/week12.sh`; nothing to delete |
| A step was interrupted | Sleep or power | Re-run; the privacy spent by the interrupted training stays in the ledger, as it should |
| Out of memory | Another heavy process | Close other programs; X5 peaks below 3 GB at batch 2048 |

## Week-12 checklist against the plan

- [x] DP settings retuned on the proxy with the grid's flaws fixed (A19)
- [x] X5: bank-partitioned vs IID arm
- [x] Membership inference on the trained model (A5, model target)
- [x] X4: the stacked ensemble across the ε sweep
- [x] Gate G3 evidence page and the pre-registered rule
- [ ] Done when: your run of `scripts/week12.sh`, then the G3 decision note
- Weeks 13–14: attribution and narrative (typology catalogue, supervised attributor, baselines, constrained narrative, X6)
