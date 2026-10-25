# Week 4 run log · 16 – 22 Nov 2026 · Behaviour and graph features

**Goal:** every account-window at every bank has its behaviour and graph features, within the memory budget.

**State:** first real-data run done (25 Oct). The review below found one design flaw, now fixed as **feature schema v2** (amendment A8), plus two questions to settle at G1. The **follow-up run** (steps F1–F5) rebuilds features with v2 and adds diagnostics; the first run's steps are kept further down for reference.

## Review of your week-4 results

**What is fine:**
- **Builds:** HI-Medium in 283 s at a peak of 1.3 GB; LI-Medium 300 s; the Small sets under a minute. Rows equal the label counts in every partition.
- **Exchange rates:** all 15 AMLworld currencies got a rate from about 200 observed pairs, and they are plausible (Euro 1.17, UK Pound 1.29, Yen 0.0095, Bitcoin about 11,900 USD).
- **Leakage check:** no feature is flagged on any dataset.
- **Signal:** the strongest single features are the ones the AML literature expects. ACH share has AUROC 0.89 on HI-Medium, consistent with Altman et al., where laundering in AMLworld over-uses ACH. Then come fan-out, new counterparties, and amount relative to history.

**What needed fixing or deciding:**

1. **Fixed: history features drifted by construction (schema v1 → v2, amendment A8).** v1 counted history from the observation start, so `age_windows`, `prior_active_windows` and `new_cp_*` grow with time. A new drift check (`finmesh diagnose`) measured PSI 7 for `age_windows` from train to validation on the fixture; above 0.25 is a large shift. A model trained on early windows would meet systematically different values in validation and test.
   - In v2 every feature depends only on the current window and the previous 72 h. `age_windows` becomes `recency_windows`, and the history rates divide by the full 72 h span.
   - The first 72 h are a training burn-in, recorded as `history_complete_from_window` in the build meta.
   - After the fix, the fixture's drift flags are gone apart from two cycle counts too rare to occur in its small validation set.
   - No model had been trained, so this is a design correction, not a post-hoc change. v1 stays frozen in the repository as a record.
2. **To decide at G1: busy accounts among the positives.** On every dataset, positives have a mean fan-out of 34–47 against 0.6 for negatives, yet `tx_out` ranks positives below chance (AUROC 0.45–0.49). A few very busy accounts that a scheme passed through once are labelled positive. They explain week 3's "90 of the top 100 by activity are positive", and any degree-based model gets credit for alerting them, though an analyst would not see them as laundering accounts.
   - `finmesh diagnose` now counts them ("incidental" positives: at least 20 legs, under 10% laundering).
   - If they are a material share, the preregistration should treat them as masked, neither positive nor negative, with the current definition kept as a sensitivity analysis.
3. **To understand: cycles rarely fire.** `cyc3` is never non-zero in LI-Medium or HI-Small validation, and `cyc4` is rare everywhere. Two causes are possible.
   - **Visibility:** a cycle through other members' accounts is invisible to one member. That is the gap evidence sharing should close, so it is the headline story.
   - **Lookback:** cycles can take longer than 24 h, which would be a feature design issue.

   `finmesh diagnose` measures both for every AMLworld pattern: whether one member sees all legs, whether the scheme fits in the lookback, and whether the signature fires.
4. **Expected, not a bug: `fmt_reinvestment_share` is 0 throughout validation.** The data has 1.9 M Reinvestment rows, the extractor counts them correctly (tested with reinvestment self-transfers), and none falls in the validation days. The drift check now flags such features as "absent later" for review at G1.

### What changed in the code

| Item | Where |
| --- | --- |
| Feature schema v2 (current); v1 kept frozen | `finmesh/schemas/features_v2.json`, `docs/protocol/features_v2.md` |
| Fixed-span history and new counterparties | `finmesh/features/account.py` |
| Drift check (PSI per feature, train after burn-in vs validation) | `finmesh/features/drift.py` |
| Positive profile and pattern visibility | `finmesh/eval/diagnostics.py`, `finmesh diagnose` |
| Amendment A8 | `docs/proposal/CHANGES.md` |

**Tests added:** history forgets beyond its span, PSI behaviour, and diagnostics on the fixture (fan patterns always fire, positives counted exactly). Both schema files are pinned.

**At scale** (32 M-row stress set, 41 M account-windows):

| Step | Time | Peak memory |
| --- | --- | --- |
| Feature build, v2 | 829 s | 2.1 GB |
| `diagnose` | about 65 s | 1.9 GB |

## Follow-up run (about 45 minutes)

### F1. Update and check

```bash
cd ~/FinMesh
git pull
uv sync
bash scripts/ci_local.sh
```

### F2. Rebuild features with schema v2 (25–40 min)

```bash
uv run finmesh features --dataset HI-Medium
uv run finmesh features --dataset LI-Medium
uv run finmesh features --dataset HI-Small
uv run finmesh features --dataset LI-Small
```

v2 features go to a new folder (`features_w6_B8_v2`). The v1 folders can be deleted afterwards to free disk, for example `rm -rf data/parquet/*/features_w6_B8_v1`. Labels do not need rebuilding.

### F3. Single-feature report (5–8 min)

```bash
uv run finmesh feature-report --dataset HI-Medium
uv run finmesh feature-report --dataset LI-Medium
uv run finmesh feature-report --dataset HI-Small
```

### F4. Diagnostics (about 2 min each)

```bash
uv run finmesh diagnose --dataset HI-Medium
uv run finmesh diagnose --dataset LI-Medium
uv run finmesh diagnose --dataset HI-Small
```

Writes `docs/eval/diagnostics_<ds>.md`. Nothing here can fail the run. Its three tables (positives, pattern visibility, drift) are the evidence for the two G1 decisions.

### F5. Tests and push

```bash
uv run pytest -m real_data -v
git add docs/eval/
git commit -m "Week 4 follow-up: schema v2 features and diagnostics on real data"
git push
```

## Review of your week-3 results

All four checks passed; nothing needs re-running except where noted in the steps below.

1. **G0 is closed: proceed on HI-Medium.** Under B8, 480 test schemes touch two or more members, inside the 450–550 I projected; pooled with LI-Medium the count is 571. The Small sets stay as development data.
2. **The harness is calibrated on real data.** On all three datasets the random scorer sits on its baseline: AUPRC equals prevalence, AUROC is 0.50–0.51, and detection falls inside the random-alert interval. LI-Medium's AUROC of 0.5073 has an interval that just excludes 0.5 (about 1.7 standard errors). That is chance, and the other two datasets are fine.
3. **Finding: FPR budgets fitted on an earlier period overshoot on the next.** On HI-Small the random scorer's worst member reached 0.13% against a 0.1% budget. At the 0.01% budget the activity scorer reached 0.02% on HI-Medium, and it spent 33% more false alerts than the random scorer at the same nominal budget. The thresholds come from train, and the score distribution shifts between periods, so methods that score differently would be compared at different effective budgets. The alerts-per-1,000-accounts-per-day budget is a per-window rank rule, so its volume is exact by construction.
   - **Recommendation for the preregistration (week 5, your decision at G1):** make 1 alert per 1,000 accounts per day the primary operating point. This is also how AML teams size analyst capacity. Keep the FPR budgets as secondary results, and always report their realised false-alert volume next to them.
4. **Finding: activity is anti-informative overall but strong at the very top.** Ranking by transaction count gives AUROC 0.46 (HI-Medium) and 0.43 (LI-Medium), yet precision at 100 is 0.90. The busiest account-windows are nearly all laundering, while a typical laundering window is quieter than a typical legitimate one. So AUROC is the wrong headline (AUPRC and budgeted detection are already the plan), and raw volume alone misleads. This shaped this week's design: features relative to the account's own history, plus structural features, not only counts.
5. **Finding: scheme metrics cover about a quarter of laundering.** HI-Medium validation has 6,374 laundering rows, but only 1,640 belong to a scheme in the pattern file. Window-level metrics count every laundering row; scheme detection (H1) counts only patterned schemes. This is how AMLworld is built, not a bug. The preregistration will state it.
6. **The language-model probe passes, with two caveats for week 13.**
   - JSON-only decoding still gave 100% valid and grounded replies, but the current grounding check only confirms that the cited typology and field names exist. Real grounding needs a semantic check: each cited field's value must be consistent with the chosen typology. That will be defined in the typology catalogue (week 13).
   - p95 latency was 29.9 s against the 30 s target, with only 20 calls. Week 13 will cap output length and keep the model loaded; no action now.
7. **A stale caption in the G0 pages is fixed.** The federation-options table still described the week-2 projection; it now says "validation count scaled by the test period's length (A5)" in the code and in the four committed pages.

## What was built

| Item | Where | Notes |
| --- | --- | --- |
| Feature schema v1 (frozen) | `finmesh/schemas/features_v1.json`, readable copy `docs/protocol/features_v1.md` | 47 features in four families; a test pins the file's SHA-256, so any change has to be released as v2 |
| Edge table | `finmesh/features/edges.py` | One streaming pass: hashed accounts, amounts in US dollars, currency and format codes. The ground-truth column is never read. Exchange rates come from the data: median received/paid per currency pair on training rows, chained to US dollars |
| Account features | `finmesh/features/account.py` | Behaviour (counts, amounts, currency and payment-format mix, active span), first-hop graph (fan-in and fan-out, amount concentration, pass-through, inbound-to-outbound delay, cross-bank, cross-member and outside shares, new counterparties) and history (age, earlier activity rate, this window relative to history) |
| Neighbourhood features | `finmesh/features/neighbourhood.py` | On each member's visible graph over 24 h: degrees, 2-, 3- and 4-cycles, scatter-gather from the source and sink side, gather-scatter hub indicator, counterparty hub degrees, hub contacts |
| Builder and store | `finmesh/features/build.py` | Writes one file per label slice and partition, **row for row in the label files' order**; `FeatureStore` reads features back as `FeatureFrame` |
| Single-feature report | `finmesh/eval/feature_report.py` | Each feature alone on validation; flags anything that nearly separates the classes as a possible leak |
| CLI | `finmesh features`, `finmesh feature-report` | |
| Label files sorted | `finmesh/eval/universe.py` | Label slices are now sorted by member, account, window: deterministic, and aligned with the feature files. **Rebuild labels once (step 2)** |

### Design decisions to review

- **Neighbourhood lookback 24 h (four 6 h windows), timing ignored inside it.** A cycle counts if all its edges fall within the last 24 h, in any order. Temporal (time-ordered) cycles are stricter and cost more; if week-5 importance shows cycles matter, a v2 can add them.
- **Hub cap 64.** Accounts with more than 64 distinct visible neighbours in the lookback are never the middle of a 2-path, which bounds the work at (edges × 64) per window. Hub contact is reported in `hub_neighbours`. Without the cap, one busy account would multiply the work by its degree squared.
- **Features use only what the holding member sees.** An account's own legs are complete, but its counterparties' other transactions are visible only when those counterparties also bank at the same member. That is the visibility gap evidence sharing will address in weeks 6–9.
- **"Run on both federations"** is read as both regimes (HI-Medium and LI-Medium) under B8, per amendments A5 and A6. The extractor takes `--option`, so a real-bank federation can be built later for the partial-participation analysis.
- **Test-partition features sit in the open area.** They hold no labels; the seal protects labels, not inputs.

## What I ran here (results)

| Check | Result |
| --- | --- |
| CI mirror (`bash scripts/ci_local.sh`) | All steps pass; 106 tests, coverage 86% |
| Hand-built account | Counts, amounts, concentration, pass-through, delays (self-transfers ignored), cross-bank, cross-member and outside shares, new counterparties and history all equal hand-computed values |
| Neighbourhood vs brute force | Degrees, 2/3/4-cycles, scatter-gather, counterparty hubs and hub contacts equal a brute-force enumeration on random graphs with a hub, for every member and window, under the visibility rule |
| Rows line up with labels | Identical keys, row for row, for train, validation and the sealed test |
| Label independence | Shuffling the ground-truth column leaves every feature unchanged |
| Determinism and slicing | Rebuilds are identical; 1 slice versus 4 slices with sub-slices gives identical features |
| Label guard | Static check covers the new modules (it caught a docstring mentioning the ground-truth column, now reworded) |
| Exchange rates on the fixture | Euro 1.1 and UK Pound 1.3 recovered exactly |

At HI-Medium scale, on a stress set of 32 M rows with heavy-tailed activity (busiest account 45,000 transactions; 2% self-transfers; cross-currency rows; seven formats), 41 M account-windows and 8 members:

| Stage | Time | Peak memory |
| --- | --- | --- |
| Edge table | 9 s | 0.2 GB |
| Neighbourhood (8 members × 40 windows) | 244 s (about 29 s per member) | 1.7 GB |
| Account features (16 slices × 4 sub-slices) | 367 s | 2.0 GB |
| **Whole build** | **622 s** | **2.0 GB** (budget 8 GB) |
| `feature-report` on 8.7 M validation account-windows | 101 s | 1.0 GB |

The first attempt peaked at 5.9 GB. Two exact fixes brought it to 2.0 GB:

- polars' `replace_strict` on a string column holds about 1.7 GB per use at 32 M rows, so lookups are now Enum casts and `when`-chains.
- Account slices are processed in sub-slices of about 1 M legs.

Real HI-Medium has fewer account-windows (about 24 M) spread over more days, so expect similar or lower memory and about 10–20 minutes on your machine.

## First run (done 25 Oct; kept for reference)

About 1 hour, most of it the two Medium builds.

### 1. Update and check (2 min)

```bash
cd ~/FinMesh
git pull
uv sync
bash scripts/ci_local.sh
```

Expected: `local CI: all steps passed`.

### 2. Rebuild the labels once (8–12 min)

The label files are now sorted so they line up with the features. Counts do not change; `docs/protocol/` files are rewritten identically.

```bash
uv run finmesh labels --dataset HI-Medium
uv run finmesh labels --dataset LI-Medium
uv run finmesh labels --dataset HI-Small
uv run finmesh labels --dataset LI-Small
```

Check with `git status`: nothing under `docs/protocol/` should show as modified.

### 3. Build features (30–45 min in total)

```bash
uv run finmesh features --dataset HI-Medium
uv run finmesh features --dataset LI-Medium
uv run finmesh features --dataset HI-Small
uv run finmesh features --dataset LI-Small
```

Each prints rows per partition, then time and peak memory per stage, and writes `docs/eval/features_<ds>.md`.

**What to look for:**
- Peak memory under 4 GB per stage.
- Rows for train and val equal the account-window counts from step 2.
- The exchange-rate table at the end of the page: AMLworld uses about 15 currencies. Any listed under "No rate for" is worth sending me, because its legs drop out of amount features.

### 4. Single-feature report (5–8 min)

```bash
uv run finmesh feature-report --dataset HI-Medium
uv run finmesh feature-report --dataset LI-Medium
uv run finmesh feature-report --dataset HI-Small
```

Writes `docs/eval/feature_signal_<ds>.md`. **What to look for:** the line "Leakage check: no feature reaches AUROC 0.95 or AUPRC 0.5 on its own". If a feature is flagged, stop and send me the page. Expect the strongest single features to reach a few times the prevalence in AUPRC, not more.

### 5. Real-data tests and push

```bash
uv run pytest -m real_data -v
git add docs/eval/
git commit -m "Week 4: features and single-feature signal on real data"
git push
```

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `feature rows do not line up with the labels` | Labels built before this week | Step 2, then `features` again |
| `membership_B8.parquet missing` | G0 not run for that dataset | `uv run finmesh g0 --dataset <ds>` |
| `features were built with a different schema file` | Schema changed after the build | `uv run finmesh features --dataset <ds>` |
| `Killed` | WSL memory cap | `.wslconfig` `memory=6GB` (week-2 run log) |
| A feature is flagged in step 4 | Possible leak | Stop; send `docs/eval/feature_signal_<ds>.md` |
| Disk full during `features` | The temporary edge table (about 1 GB for Medium) | Free space; it is deleted after each build |

## Week-4 checklist against the plan

- [x] Behaviour features per account-window from each bank's own view
- [x] Graph features: in- and out-degree, fan-in and fan-out statistics, new-counterparty share, visible short cycles of length 2–4, scatter-gather and gather-scatter indicators, pass-through ratio, inbound-to-outbound delay, cross-bank and cross-currency shares
- [x] Time-bucketed chunks (one day plus a 24 h lookback) with bounded cycle length and a hub cap
- [x] Extractor deterministic and never reads labels (tests: rebuild equality, ground-truth shuffle, static guard, `FeatureFrame`)
- [x] Throughput and peak memory per member, logged in `docs/eval/features_<ds>.md`
- [x] Feature schema frozen in `finmesh/schemas/` (v1, superseded before any model by v2, amendment A8)
- [x] Done when: features for all federation banks written to Parquet within 8 GB on real data (HI-Medium peak 1.3 GB, 25 Oct; v2 rebuild in step F2)

## Open items for you

1. Run the follow-up steps F1–F5 and push.
2. At G1 (week 5), decide, with the diagnostics in hand:
   - the primary operating point (week-3 review item 3; recommendation: alerts per 1,000 accounts per day);
   - how to treat incidental positives (week-4 review item 2; recommendation: mask them, keep the current label as a sensitivity analysis).
