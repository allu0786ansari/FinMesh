# FinMesh preregistration

**Status: draft.** It is frozen, committed and tagged `g1` once the Gate G1 evidence (validation only) has been reviewed and section 9 is filled in. After the tag, nothing below changes except through an amendment in `docs/proposal/CHANGES.md` made before the results it affects exist. The sealed test is opened only in week 18.

Proposal: `docs/proposal/FinMesh_Proposal_v2.md`, with amendments A1–A11.

## 1. Data, federation and splits

- **Datasets:**
  - Headline: IBM AMLworld **HI-Medium**.
  - Second regime: **LI-Medium**.
  - Development and replication: HI-Small and LI-Small (A6).
- **Licences:** data CDLA-Permissive-2.0, code MIT.
- **Observation window:** the dense period only (A1), found by the label-free rule in `finmesh/data/splits.py`.
- **Windows:** 6 h, non-overlapping. Train / validation / test take 60 / 20 / 20% of the windows, with a one-window gap at each boundary.
  - Plans are frozen in `docs/protocol/split_plan_<dataset>.json` and checked by `tests/integration/test_real_data_week3.py`.
- **Federation:** **B8**, eight institutions formed by grouping banks, balanced by accounts, so every account is held by a member (A5). Real-bank federations (A8–A64) are a secondary partial-participation analysis.
- **Visibility:** a member sees every transaction with one end at one of its accounts, including the counterparty's account and bank; nothing beyond that (`finmesh/data/visibility.py`).
- **Features:** schema **v3** (`finmesh/schemas/features_v3.json`, SHA-256 prefix `550f9243bb6881be`). There are 47 features in four families, and every feature depends only on the current window and the previous 72 h (A8, A11). The first 72 h are a training burn-in.
  - **Member view:** what each bank sees. Used by S0 and by every sharing level as the local input.
  - **Pooled view:** the full graph. Used only by the oracle.

## 2. Unit, labels and schemes

- **Unit:** the account-window, i.e. an account held at a member in one window with at least one leg. Inactive accounts are never scored.
- **Primary label (A9):** positive if the window touches an unmasked laundering leg and is not incidental. Masked if it touches only legs of schemes assigned to another partition, or if it is incidental. Otherwise negative.
  - **Incidental:** at least 20 legs, of which under 10% are unmasked laundering legs.
  - Masked windows count in neither precision nor recall, but alerts on them use budget.
- **Sensitivity label ("touch"):** the original definition, with incidental windows positive. It is reported next to every headline result.
- **Scheme event:** one pattern-file scheme.
  - It is assigned to the partition of its first in-window leg; its legs in other partitions are masked there.
  - Scheme detection counts only the scheme's non-incidental account-windows in its own partition.

## 3. Operating points

- **Primary (A10):** 1 alert per 1,000 accounts per day per member. Each member alerts its top k account-windows in every window, with k = round(accounts × 6/24 / 1000). Alert volume is exact by construction.
- **Secondary:** 0.1% and 0.01% window FPR per member. Each is always reported with its realised false-alert volume.
  - For validation reports, thresholds come from the held-out last 20% of the training windows (out of sample for every model).
  - For the test run, they come from validation.
- Calibration and every fusion or disclosure parameter come from validation only (CC2).

## 4. Detection definitions

- **Detected:** at least one of the scheme's account-windows, at any member, is alerted within **12 windows (72 h)** of the scheme's first window.
- **Linked (primary RQ1 metric):** at least two of the scheme's accounts fall in one incident within the same delay.
  - **Linked across members:** those accounts are held by different members.
- **Incidents:**
  - **S0:** a member links its own alerted account-windows when the accounts transacted directly within the 72 h ending at the later window, and the windows are less than 72 h apart. One account's alerts within 72 h form one case. Incidents are the connected components (`finmesh/fusion/local.py`).
  - **Oracle:** the same rule with every member's alerts visible.
  - **S1–S4 and PD:** the fusion layer of week 7. Its rule is fixed and committed before any X1 result exists.
- **Random-alert baselines:**
  - Any-alert detection: exact, 1 − Π(1 − p) over the scheme's account-windows at member alert rates p.
  - Linked detection: 20 draws of random alerts with the same count per member and window, linked by the same rule as the scorer.

## 5. Hypotheses and performance targets

From the proposal, sections 4.2 and 11.3. Thresholds marked *provisional* may be revised once, from validation only, at G1 (section 9), and are then frozen.

| ID | Statement | Test |
| --- | --- | --- |
| H1a / PT1 | At the primary budget, S2 raises linked scheme detection over S0, and is above the random-alert baseline | Paired bootstrap over schemes, 95% CI excluding 0, Holm across the sharing levels compared with S0 |
| H1b / PT1 | S2 recovers at least **60%** (provisional) of the oracle gain: (S2 − S0) / (oracle − S0) in linked detection | Ratio with a bootstrap CI; reported only if oracle − S0 meets the G1 criterion |
| H1c / PT2 | Inference attacks on S1 and S3 (ε ≤ 2) stay within the stated margin of prior-only baselines at 1% FPR; S4 is significantly higher; S3 is monotone in ε | Attack TPR at 0.1% and 1% FPR with CIs |
| H1d / PT3 | Progressive disclosure reaches at least **80%** (provisional) of the S2 gain with full evidence disclosed on fewer than **half** (provisional) as many accounts | Ratio and disclosure count with CIs |
| H2a / PT4 | Federated DP neural scorer at ε ≤ 10 reaches at least **70%** (provisional) of the centralised non-private AUPRC and exceeds the mean local-only neural AUPRC | AUPRC ratio with CI |
| PT4b | S0 GBDT on every feature beats S0 GBDT on behaviour and history only, in AUPRC | Paired account bootstrap, CI excluding 0 |
| H2b | At the same ε, the account-level privacy unit loses measurably more AUPRC than the window-level unit | Difference with CI |
| H3a / PT5 | Attribution accuracy on fused evidence rises with sharing level (S0 < S2) and beats the baselines | Paired bootstrap over schemes |
| H3b / PT5 | At least **95%** of raw narrative outputs are grounded before validation (A7: JSON-only decoding; grounding defined semantically in the week-13 typology catalogue) | Proportion with CI |

Every result is reported whether or not its hypothesis holds; a missed target is a finding.

## 6. Models and training (fixed now, not tuned on validation)

| Configuration | Model | Features | Rows | Linking |
| --- | --- | --- | --- | --- |
| S0-B | LightGBM per member | behaviour + history (24) | member's own | local |
| S0-BG (= S0) | LightGBM per member | all 47, member view | member's own | local |
| Oracle | One LightGBM | all 47, pooled view | every member's rows | pooled |
| Isolation Forest, PCA | Per member, unsupervised | all 47, signed-log, robust scaling | 200 k-row sample | local |
| Random, activity | Reference scorers | — | — | local |

- **LightGBM settings** (`finmesh/models/gbdt.py`): learning rate 0.05, 31 leaves, 50 minimum rows per leaf, feature and bagging fraction 0.8, L2 regularisation 1. At most 1,000 rounds, with early stopping after 50 rounds without gain in average precision on the held-out training windows.
- **Training rows** (`finmesh/training/data.py`):
  - Training partition after the burn-in; the last 20% of training windows are held out.
  - Masked rows are excluded.
  - Every positive is kept. Negatives are kept with probability 0.1, by a fixed hash, and weighted ×10.
- **Calibration:** isotonic per member, fitted on validation and applied at test.
- **Later configurations** (federated neural scorer, sharing levels, fusion, attribution) are specified in their own weeks, before their results exist, and recorded here by amendment.

## 7. Seeds and statistics

- **Seeds:**
  - Headline configurations (S0-BG, oracle, S2, PD): 5 seeds, 0–4.
  - Every other configuration: 3 seeds, 0–2.
  - A seed fixes model training and negative sampling; bootstrap seeds are fixed at 0.
- **Combining seeds:** per-scheme outcomes are averaged over seeds before the cluster bootstrap over schemes (1,000 replicates). Window metrics are averaged over seeds, with a Poisson bootstrap over accounts (200 replicates on validation, 1,000 at test).
- **Comparisons:** the paired bootstrap on the same schemes and accounts, with Holm correction across the sharing levels compared with S0 within each metric. Two-sided, α = 0.05.

## 8. Analysis plan

- **Primary analysis:** H1a on HI-Medium **test**, linked detection at the primary budget, label primary.
- **Secondary analyses**, reported in full:
  - LI-Medium;
  - any-alert detection;
  - the FPR operating points;
  - the touch label;
  - time to detect;
  - the Small datasets as replication.
- **Test discipline:** each frozen configuration and seed is evaluated once on test, through `finmesh.eval.sealed.open_sealed_test`, which logs every opening (CC2).

## 9. Gate G1 (filled in after the validation run)

**Criterion, fixed before the run:** the oracle beats S0 by a margin worth studying when, on **HI-Medium validation** at the primary budget, the paired 95% CI of oracle − S0 linked detection excludes 0 **and** the estimate is at least 0.05 (5 points). If it does not, the reason is recorded before any sharing level is built, because H1b measures the share of this gap that sharing recovers.

| Item | Value |
| --- | --- |
| Oracle − S0 linked detection, HI-Medium validation | *pending* |
| Criterion met | *pending* |
| PT4b direction on validation (informational) | *pending* |
| Provisional thresholds (H1b 60%, H1d 80% and one half, H2a 70%) | *pending: unchanged or revised, with the validation evidence* |
| Decision | *pending* |
