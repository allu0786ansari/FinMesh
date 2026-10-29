# FinMesh preregistration

**Status: frozen at Gate G1, 26 Oct 2026 (tag `g1`).** Nothing below changes except through an amendment in `docs/proposal/CHANGES.md` made before the results it affects exist. The sealed test is opened only in week 18.

Proposal: `docs/proposal/FinMesh_Proposal_v2.md`, with amendments A1–A11; A12–A17 were added after the freeze, through `docs/proposal/CHANGES.md`.

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
  - **S1–S4 and PD:** the fusion layer of week 7, fixed by amendment A13 (section 6a) before any real-data X1 result: triage by a cross-fitted per-member stacker, then the pooled linking rule.
- **Random-alert baselines:**
  - Any-alert detection: exact, 1 − Π(1 − p) over the scheme's account-windows at member alert rates p.
  - Linked detection: 20 draws of random alerts with the same count per member and window, linked by the same rule as the scorer.

## 5. Hypotheses and performance targets

From the proposal, sections 4.2 and 11.3. Thresholds marked *provisional* may be revised once, from validation only, at G1 (section 9), and are then frozen.

| ID | Statement | Test |
| --- | --- | --- |
| H1a / PT1 | At the primary budget, S2 raises linked scheme detection over S0, and is above the random-alert baseline | Paired bootstrap over schemes, 95% CI excluding 0, Holm across the sharing levels compared with S0 |
| H1b / PT1 | S2 recovers at least **60%** (provisional) of the oracle gain: (S2 − S0) / (oracle − S0) in linked detection. **A14:** the ceiling is the relational oracle (section 6a); the preregistered oracle ratio is reported alongside | Ratio with a bootstrap CI; reported only if oracle − S0 meets the G1 criterion |
| H1c / PT2 | Inference attacks on S1 and S3 (ε ≤ 2) stay within the stated margin of prior-only baselines at 1% FPR; S4 is significantly higher; S3 is monotone in ε. **A15:** margin 0.05 on the upper 95% bound of (attack − prior) TPR at 1% FPR, every assessable A2/A3 target (section 6b) | Attack TPR at 0.1% and 1% FPR with CIs |
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
| S0-BG-noart, oracle-noart | As S0-BG and the oracle | without the 7 payment-format shares and `self_tx` (39 features) | as above | as above |

- **LightGBM settings** (`finmesh/models/gbdt.py`): learning rate 0.05, 31 leaves, 50 minimum rows per leaf, feature and bagging fraction 0.8, L2 regularisation 1. At most 1,000 rounds, with early stopping after 50 rounds without gain in average precision on the held-out training windows.
- **Training rows** (`finmesh/training/data.py`):
  - Training partition after the burn-in; the last 20% of training windows are held out.
  - Masked rows are excluded.
  - Every positive is kept. Negatives are kept with probability 0.1, by a fixed hash, and weighted ×10.
- **Calibration:** isotonic per member, fitted on validation and applied at test.
- **Later configurations** (federated neural scorer, sharing levels, fusion, attribution) are specified in their own weeks, before their results exist, and recorded here by amendment.

## 6a. Fusion layer (amendment A13, week 7)

- **Candidates:** every validation account-window with calibrated probability ≥ 0.01 (the evidence floor) or an S0 alert. Each asks, through the protocol of week 6, about its counterparties at other members within the 72 h lookback.
- **Evidence features per candidate** (`finmesh/fusion/triage.py`):
  - S1: own logit; requests sent, refused, answered with an alert flag; inbound requests about the candidate and the highest requester bucket.
  - S2: S1 plus, over counterparty records, the count, highest and summed probability bucket, highest deviation magnitude, fan-in, fan-out and pass-through buckets.
  - S4: S2 plus the mean counterparty embedding (8 dimensions).
- **Primary fusion:** per member, `StandardScaler` + `LogisticRegression` (L2, C = 1, `lbfgs`), fitted on unmasked candidates of one validation half (windows 39–44 or 45–50) and scoring the other. Non-candidates keep their S0 probability; each member cuts at the primary budget.
- **Linking:** S1+ and propagation use the pooled rule of section 4; S0 the local rule.
- **Secondary fusion rules** (reported, never selected): noisy-OR and k-of-n (k = 1), defined in `finmesh/fusion/triage.py`.
- **Propagation (PD):** plaintext score propagation, own probability + 0.5 × the strongest cross-member counterparty probability in the lookback.
- **X1 on validation:** seeds 0–2; H1b recovery (level − S0) / (oracle − S0) in linked detection with a scheme bootstrap. Only test decides H1b.

### Relational oracle (amendment A14)

- Pooled oracle probabilities, isotonic-calibrated per member on the held-out end of training.
- Candidates: calibrated oracle probability ≥ 0.01, or an oracle alert.
- Features (`finmesh/training/relational.py`): own oracle logit; over every counterparty in the federation (any member, both directions) within the lookback, their number, how many the oracle alerted, the highest and the summed oracle probability.
- The section-6a stacker, cross-fitted on the validation halves; pooled linking. It is H1b's ceiling. `oracle+propagation` (own + 0.5 × strongest counterparty) is reported alongside.

## 6b. Evidence privacy and the leakage audit (amendment A15, week 8)

- **S3** (`finmesh/sharing/ldp.py`): every record field except the time bucket and alert flag through k-ary randomised response at ε / 20 per field. Releases are memoised per record. At most ε = 8 per account and epoch, then the S1 answer. Sweep ε ∈ {0.5, 1, 2, 4, 8}.
- **PD** (`finmesh/sharing/node.py`): the S1 answer, plus the S2 record when the requester's score bucket is at least τ. Sweep τ ∈ {2, 3, 4}.
- **Fusion** for S3 and PD: the section-6a stacker on the S2 feature set, fitted on evidence released through the same mechanism.
- **H1d:** PD's share of S2's gain over S0, and its accounts disclosed as a share of S2's. S1 is reported as the reference.
- **Attacks** (`finmesh/training/audit.py`, seed 0 of each X1 run):
  - A1: targets are the tokens of other members' evidence records. Candidates are the accounts at other members that the adversary's customers traded with up to the end of validation. Hashing tokenises every candidate offline. The OPRF tokenises only within the spare per-epoch budget, deployed (250,000) and sized (2 × the largest legitimate use). Reported as expected re-identification.
  - A2: the queried account transacted with a third member in the window its answer describes.
  - A3: outgoing amount in the top decile; fan-in in the top decile; pass-through ratio ≥ 0.9.
  - A2 and A3 adversary: a gradient-boosted classifier trained on the true attributes of half the queried accounts (split by account), tested on the other half. Baseline: a prior-only classifier on its own accounts in the request, its score bucket, the window and the two banks.
  - At most 200,000 targets, sampled by account hash. Metrics: TPR at 0.1% and 1% FPR and AUC, with an account-cluster bootstrap (200 replicates).
- **H1c margin:** the upper 95% bound of (attack − prior) TPR at 1% FPR is at most 0.05 on every assessable target.

### Amendment A16 (week 9)

- **S3:** every request gets a record. Accounts without one get a dummy (probability bucket 0, no deviation, counters missing). The time field is the end of the requested range. Releases are memoised per record and epoch.
- **Token budgets** (`finmesh/schemas/token_budgets.json`): twice the largest legitimate per-bank, per-epoch use on validation. HI-Medium 74,510; LI-Medium 87,580; 250,000 elsewhere. PT2 is judged at these budgets.
- **A4:** rotation simulated at mid-validation. Each second-half record is ranked among up to 99 first-half records from the same responder by similarity (negative Hamming distance over the fields; at S4, distance over the standardised fields and embedding). Reported as hit@1 against chance. S3 is released afresh in each half.
- **A5:** a classifier on S4's disclosure (deviation indices, directions, magnitude buckets, embedding) separating each member's autoencoder training rows from its other training rows. At most 5,000 of each per member; train on half by account.
- **A6:** the responder predicts its own candidate's label from its own score, then from its own score plus the requests it received (count, highest requester bucket). The gain is reported.
- **H1b** is also reported against the stronger of the relational oracle and oracle + propagation (sensitivity).

## 6c. Neural scorer and federated DP (amendment A17, weeks 10–12)

- **Engine:**
  - NumPy DP-SGD with exact per-unit clipping (`finmesh/models/neural.py`, `finmesh/federation/dpsgd.py`);
  - the `dp-accounting` RDP accountant for the Poisson-subsampled Gaussian mechanism (`finmesh/federation/accountant.py`);
  - FedAvg in process, equal weights, all members every round (`finmesh/federation/fedavg.py`).
- **Model:** a fixed piecewise-linear encoding of every feature (bins by feature kind, a missing indicator, nothing estimated from data). Then an MLP 64-32-1 with ReLU and no batch normalisation. Weighted cross-entropy, weight 10 on positives.
- **Training rows:** those of the GBDT (section 6). Adam, lr 1e-3; batch 512 per client step; 50 rounds × 20 local steps; clip norm 1. The centralised reference takes 1,000 steps of 512 × members rows.
- **Privacy:**
  - ε ∈ {1, 3, 10}; δ = 0.1 / N per client; the noise multiplier is calibrated once for 1,000 steps.
  - Accountants persist, a budget guard refuses extra steps, and every private training is appended to a privacy ledger.
  - The window unit comes in week 10. The account unit (one account's bag of at most k windows) and the degree cap come in week 11, specified before their results.
- **X4 (part 1):** centralised, local-only, FedAvg and FedAvg + DP MLPs, and the local GBDT, on validation. AUPRC is pooled over the federation's account-windows, averaged over seeds 0–2, with a paired Poisson bootstrap over accounts.
- **H2a:** FedAvg + DP at ε ≤ 10 reaches at least 0.70 of the centralised MLP's AUPRC and exceeds the local-only MLP's.

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
  - the Small datasets as replication;
  - **artefact ablation** (added at G1): S0 and the oracle refitted without the payment-format shares and `self_tx`, the two strongest features in every model and likely AMLworld simulator quirks. The oracle − S0 linked-detection gap is reported with and without them.
- **Decomposition** (informational, no hypothesis): S0 alerts linked with the pooled rule. It separates how much of the oracle gain comes from linking alerts across members and how much from better detection.
- **Test discipline:** each frozen configuration and seed is evaluated once on test, through `finmesh.eval.sealed.open_sealed_test`, which logs every opening (CC2).

## 9. Gate G1 (filled in after the validation run)

**Criterion, fixed before the run:** the oracle beats S0 by a margin worth studying when, on **HI-Medium validation** at the primary budget, the paired 95% CI of oracle − S0 linked detection excludes 0 **and** the estimate is at least 0.05 (5 points). If it does not, the reason is recorded before any sharing level is built, because H1b measures the share of this gap that sharing recovers.

| Item | Value |
| --- | --- |
| Oracle − S0 linked detection, HI-Medium validation | **0.508**, 95% CI [0.465, 0.550] (S0 0.174, oracle 0.682; 551 schemes) |
| Criterion met | **Yes**; also on LI-Medium: 0.538 [0.441, 0.634] |
| Where the gap is | Almost all in linking: any-alert detection S0 0.864, oracle 0.886 (difference 0.022 [−0.002, 0.045]); 0.635 of schemes linked across members by the oracle, 0 by S0 by construction |
| PT4b direction on validation (informational) | Graph features help: S0-BG − S0-B AUPRC +0.036 [0.030, 0.044] on HI-Medium, +0.012 [0.006, 0.018] on LI-Medium |
| Provisional thresholds (H1b 60%, H1d 80% and one half, H2a 70%) | **Unchanged** (owner, 26 Oct). Validation gives no evidence for H1d or H2a; for H1b the gain is large and mostly cross-member linking, which sharing is designed to provide |
| Decision | **Proceed to the sharing layer (weeks 6–9)** with RQ1 as the headline. Evidence: `docs/gates/G1_evidence.md`, `docs/eval/baselines_<ds>.md`; note `docs/gates/G1.md` |
