# Week 5 run log · 23 – 29 Nov 2026 · Baselines and preregistration (Gate G1)

**Goal:** the local-only (S0) and pooled-oracle reference points exist, and the targets are frozen.

**State:** code complete and tested on the fixture, on synthetic data with known answers, and at HI-Medium scale. Your run produces the G1 evidence. After you push it, I fill in section 9 of the preregistration and write the G1 decision note, and you confirm before the repository is tagged `g1`.

## Decisions taken at G1 preparation (25 Oct, from the week-4 diagnostics)

| ID | Decision | Why |
| --- | --- | --- |
| A9 | Incidental positives (at least 20 legs, under 10% laundering) are **masked**; the original label is reported as a sensitivity analysis | 2–6% of positives, but all of the positives in the top 100 and top 1,000 by activity |
| A10 | Primary operating point: **1 alert per 1,000 accounts per day**; FPR budgets secondary | FPR thresholds overshoot on the next period; the per-day rule fixes alert volume exactly |
| A11 | Feature schema **v3**: neighbourhood lookback 72 h | Median scheme duration 22–52 h; only 31–51% of schemes fit in 24 h |

All three are in `docs/proposal/CHANGES.md` and the preregistration.

## What was built

| Item | Where | Notes |
| --- | --- | --- |
| Labels with incidental masking (A9) | `finmesh/eval/universe.py`, `sealed.py` | `incidental` flag per account-window; `EvalStore.partition(p, variant="touch")` gives the sensitivity label; scheme detection ignores incidental windows |
| Feature schema v3 (A11) | `finmesh/schemas/features_v3.json`, `docs/protocol/features_v3.md` | Same 47 features; 72 h neighbourhood lookback |
| Pooled view | `finmesh features --view pooled` | The oracle's features: every transaction visible, rows keyed and ordered exactly like the member view. Account-level features are shared; the neighbourhood is recomputed on the full graph |
| Faster, bounded neighbourhood pass | `finmesh/features/neighbourhood.py` | Active accounts in hash parts; cycles probe only edges into active accounts; 4-cycle overlaps only for pairs with 2-paths both ways. Exact: brute-force tests unchanged |
| Local incidents (S0) and pooled incidents (oracle) | `finmesh/fusion/local.py` | Alerted account-windows linked when the accounts transacted within 72 h; same-member only for S0 |
| Random baseline for linked detection | `finmesh/eval/harness.py` | 20 draws with the same alert count per member and window, linked by the same rule |
| Models (label-free) | `finmesh/models/gbdt.py`, `unsupervised.py`, `calibration.py` | LightGBM with fixed settings; Isolation Forest and PCA reconstruction; isotonic calibration |
| Training (where labels meet features) | `finmesh/training/` | Burn-in, held-out last 20% of training windows, 10% negative sampling with ×10 weights; S0-B, S0-BG, oracle, unsupervised; evaluation, paired comparisons, calibration, thresholds for test |
| CLI | `finmesh baselines`, `finmesh g1` | |
| Preregistration (draft) | `docs/protocol/preregistration.md` | Everything fixed except section 9, which waits for your validation run |

### Choices to review

- **The G1 criterion** (preregistration, section 9): on HI-Medium validation at the primary budget, the oracle beats S0 in linked detection with a 95% CI excluding 0, by at least 5 points. If the gap is smaller, sharing cannot show much, and we decide what to do before building it.
- **Detection delay 72 h** after a scheme's first window. Most schemes run 1–2 days, so 72 h leaves time to see a scheme unfold without crediting very late alerts.
- **LightGBM settings fixed, not tuned.** Tuning on validation would spend the data that G1 judges on. The settings are standard for tabular fraud work; early stopping uses the held-out training windows.
- **S0 can only link its own accounts.** S0 incidents never cross members, so S0's linked detection across members is 0 by definition. The headline compares total linked detection, which S0 can achieve inside a member.

## What I ran here (results)

| Check | Result |
| --- | --- |
| CI mirror (`bash scripts/ci_local.sh`) | All steps pass, including the pooled view and a small baselines run on the fixture |
| Incidental masking | A planted busy account (1 laundering leg among 31) is masked in the primary label, positive in the touch label, and absent from scheme detection |
| Incidents | Hand-built cases: same-member links, no cross-member links at S0, cross-member links in the pooled view, links too old or after both alerts refused, one account's repeated alerts form one case |
| Neighbourhood | Still equal to brute force; splitting active accounts into parts changes nothing |
| Pooled view | Same rows and order as the member view; account features identical; degrees never smaller |
| Models | LightGBM learns a planted signal (AUROC above 0.9) and is deterministic for a seed; outliers score high under Isolation Forest and PCA; isotonic calibration lowers the Brier score |
| Training rows | Every positive kept, burn-in and masked rows excluded, negatives sampled and weighted ×10, same rows for the same seed |

At HI-Medium scale (32 M-row heavy-tailed stress set, 41 M account-windows):

| Step | Time | Peak memory |
| --- | --- | --- |
| `labels` (with A9) | 129 s | 1.2 GB |
| `features` (member view, v3) | 1,393 s | 3.0 GB |
| `features --view pooled` | 1,291 s | 3.2 GB |
| `baselines` (7 scorers, 1,000 scheme and 200 window replicates, 20 random-linking draws) | 959 s | 3.4 GB |

Two exact fixes found by this run:

- The neighbourhood pass now probes only edges into active accounts and computes 4-cycle overlaps only where 2-paths run both ways, which made it about 1.5x faster.
- The runner keeps one key-and-label frame per partition instead of one per scorer, which brought baselines from 4.7 GB to 3.4 GB.

The stress set is denser than the real data (3.2 M rows per day against 2 M) and runs here on 2 cores. In week 4 your machine built real HI-Medium about 3 times faster than this stress set, so expect roughly a third of these times.

## What you run on your machine

About 2 hours in total, almost all of it waiting. Run the Medium datasets first; the Small ones are optional replication.

### 1. Update and check (5 min)

```bash
cd ~/FinMesh
git pull
uv sync                      # adds LightGBM, scikit-learn, SciPy
bash scripts/ci_local.sh
```

### 2. Rebuild labels with incidental masking (A9) (10 min)

```bash
uv run finmesh labels --dataset HI-Medium
uv run finmesh labels --dataset LI-Medium
```

Positives drop slightly (by the incidental count) and masked rows rise by the same amount. `docs/protocol/eval_counts_*.json` change accordingly; commit them in step 6.

### 3. Build features, schema v3, both views (40–60 min)

```bash
uv run finmesh features --dataset HI-Medium
uv run finmesh features --dataset HI-Medium --view pooled
uv run finmesh features --dataset LI-Medium
uv run finmesh features --dataset LI-Medium --view pooled
```

The pooled view needs the member view first. Old feature folders can be deleted afterwards: `rm -rf data/parquet/*/features_w6_B8_v1 data/parquet/*/features_w6_B8_v2`.

### 4. Baselines (20–40 min per dataset)

```bash
uv run finmesh baselines --dataset HI-Medium
uv run finmesh baselines --dataset LI-Medium
uv run finmesh g1
```

Writes `docs/eval/baselines_<ds>.md` and `docs/gates/G1_evidence.md`. The last line of each `baselines` run prints the G1 number: `oracle - S0 linked +x.xxx [low, high]`.

**What to look for:**
- **Random** detected inside its random-alert interval.
- **S0-BG and the oracle** well above random in AUPRC and detection.
- **The oracle above S0** in linked detection, which is the G1 criterion.
- If **S0-B beats S0-BG**, that is PT4b failing on validation: a finding to note, not an error.

### 5. Optional: Small datasets (about 20 min)

```bash
for d in HI-Small LI-Small; do
  uv run finmesh labels --dataset $d
  uv run finmesh features --dataset $d
  uv run finmesh features --dataset $d --view pooled
  uv run finmesh baselines --dataset $d
done
```

### 6. Tests and push

```bash
uv run pytest -m real_data -v
git add docs/eval/ docs/gates/ docs/protocol/
git commit -m "Week 5: baselines and G1 evidence on real data"
git push
```

Do **not** tag yet: I fill in section 9 of the preregistration from your results, then you review it and tag `g1`.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `labels predate amendment A9` | Labels from week 3 or 4 | Step 2 |
| `features_w6_B8_v3/meta.json missing` | v3 features not built | Step 3 |
| `... --view pooled` missing | Pooled view not built | `finmesh features --dataset <ds> --view pooled` |
| `does not line up` | Labels rebuilt after features | Rebuild features (step 3) |
| `Killed` during features | WSL memory cap | `.wslconfig` `memory=6GB` or more |
| LightGBM import error about `libgomp` | OpenMP runtime missing | `sudo apt install libgomp1` |

## Week-5 checklist against the plan

- [x] Local LightGBM per bank, behaviour-only and behaviour plus graph (feeds PT4b)
- [x] Pooled-data oracle GBDT (pooled view)
- [x] Isolation Forest and PCA-reconstruction baselines
- [x] Isotonic calibration and per-bank thresholds on validation data (thresholds for test saved in the artifact)
- [ ] S0 and oracle results on validation, linked and any-alert detection against the random-alert baseline (your step 4)
- [x] Time per configuration recorded in the artifact; seed plan fixed (5 seeds for headline configurations, 3 elsewhere)
- [x] `docs/protocol/preregistration.md` drafted; section 9 waits for step 4
- [ ] G1 note and tag `g1` (after your run)
