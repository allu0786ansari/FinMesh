# Amendment A25: improvements, confirmed on fresh data

**Status: signed 6 Nov 2026; being built. No Large data opened.**
**Signed off by:** Allaudin Ansari· **Date:** 6 Nov 2026 · **Frozen commit (before any Large opening):** —

## Why this amendment exists

The week-18 sealed test is spent. Its results stay the paper's primary, pre-registered results, unchanged (`docs/eval/test/RESULTS.md`).

The test showed weak points a reviewer would attack:

- one synthetic dataset family, with a share of the gap coming from suspected artefact features;
- gains that are about linking schemes rather than detecting them;
- an alert flag that leaks an account attribute on LI-Medium (H1c);
- a token budget that broke on the busier test days;
- an unfaithful 3B narrative model;
- no anchor against the standard AMLworld benchmark.

**Any fix scored on the week-18 test would be tuning on the test set.** So every item here follows the same three rules:

1. **Develop** on HI-Medium and LI-Medium training and validation only. The week-18 test partition is not reused for any choice.
2. **Freeze** each choice by the rule written below, before any fresh data is opened.
3. **Confirm** on data the project has never touched: windows of **HI-Large and LI-Large**, which are independent AMLworld simulation runs (97 days, about 2.1 M accounts, about 180 M transactions each). Each Large window gets its own train, validation and sealed test, through the same seal and access log as week 18.

The A25 results are then reported as a pre-registered confirmatory extension, next to the week-18 results and never in place of them.

## Priority order

| Priority | Item | Answers the objection | Confirms on | Effort |
| --- | --- | --- | --- | --- |
| **P1** | Fresh replication on HI-Large and LI-Large, with artefact-free variants | "One synthetic dataset; maybe simulator artefacts" | Large test | 2 days code + 2–3 nights |
| **P2** | Case-quality metrics | "Sharing only links, it doesn't detect more" | Large test | 1–2 days |
| **P3** | Protecting the alert flag | "The flag leaks an attribute (H1c, LI)" | Large test | 3–4 days |
| **P4** | Adaptive token budget | "The budget broke on busier days" | Week-18 traffic replay (label-free) + Large | 1 day |
| **P5** | Narrative: larger local models, and a select-then-template design | "The narrative is unfaithful" | Large test | 2–3 days + model runs |
| **P6** | Benchmark anchor on the standard AMLworld split | "The detector isn't compared with published results" | The benchmark's own split | 2–3 days |
| **P7** | Related-work positioning | "How does this differ from prior collaborative AML?" | — (writing) | 1 day |
| — | Federated DP (H2) | — | No new work: reported as a finding (a strong local detector leaves little for a federated model to add) | 0 |

---

## P1. Fresh replication on HI-Large and LI-Large

**Window rule (label-free, fixed now).**

- Ingest each Large set and find its dense period with the A1 rule (`finmesh/data/splits.py`).
- Take the **16 consecutive days ending at the end of the dense period** (Medium's length), cut by calendar day.
- Window length 6 h; splits 60/20/20 by window with one-window gaps, as in G0; federation B8 built by the same rule; features v3 unchanged.
- If a window lacks at least 8 test windows or 100 pattern-labelled test schemes, G0's fallback order applies. That is recorded before any model is trained.

**Windows found (7 Nov, label-free):** both Large sets give **21 Oct to 5 Nov 2022** (16 dense days, 12 test windows).
- **HI-Large-W16:** 559 multi-member test schemes, band **proceed**.
- **LI-Large-W16:** 78 multi-member (92 visible) test schemes, **case-study band**. That is the same band as LI-Medium (91) in G0, so by G0's order it proceeds as the second regime with wide intervals, exactly as LI-Medium did.

Recorded before any model is trained on either window.

**Token budget, sized before any test:** `finmesh size-budget --dataset <window>` measures the largest legitimate per-bank, per-epoch use on the window's **validation** traffic (seed 0, validated calibration, every candidate asking). It writes twice that into `finmesh/schemas/token_budgets.json`, which is committed before the frozen commit.

**Configurations:**

- S0, S1, S2, PD at τ ∈ {2, 3, 4}, the oracle and the relational oracle, with the frozen fusion of A13–A14 and A24a.
- Plus the artefact-free versions **S0-noart, S1-noart, S2-noart and oracle-noart**: the same pipeline without the 7 payment-format shares and `self_tx`.
- Plus the protected flag chosen on validation (P3, `S1F[gate=2]`), and the stronger-detector track **S0+, S2+, oracle+** (P6 adequacy; see "Selections made on validation").
- Parameters are fitted on the Large window's own validation partition, exactly as A24/A24a did for Medium.

**Seeds:** headline configurations 0–4, others 0–2. The audit runs on seed 0.

**Token budget:** sized by the A16 rule on the Large window's validation traffic. Every legitimate request is served, and the shortfall is reported (A24a).

**Rules, each Large dataset separately:**

| ID | Rule |
| --- | --- |
| H1a-L | S2 − S0 linked detection, paired 95% CI above 0, Holm across the sharing configurations, and S2 above random |
| H1b-L | S2 ≥ 0.60 of the relational oracle's gain over S0, if oracle − S0 meets the G1 criterion |
| H1a-L-noart | S2-noart − S0-noart linked detection, CI above 0. This says whether the headline survives without the suspected artefacts |
| H1d-L | As H1d, **with S1 as the reference**: PD reaches ≥ 0.80 of S2's gain with < 0.5 of its disclosure; reported as uninformative if S1 alone reaches 0.80 |

**Machine time:** ingesting each Large file (about 16 GB of CSV) is a one-off of 1–2 h. Each window then costs about as much as a Medium dataset in week 18: 8–9 h for X1 with the audit.

## P2. Case-quality metrics (definitions fixed now)

They are computed for every configuration of P1 on the Large tests, at the primary budget and with the 72 h delay, from the same incidents as linked detection:

- **Case completeness:** for each detected scheme, the largest share of its non-incidental accounts found in one incident; mean over schemes.
- **Fragmentation:** for each detected scheme, the number of distinct incidents holding its alerted accounts; mean over schemes (lower is better).
- **Workload per linked scheme:** alerts raised ÷ schemes linked. The alert volume is fixed by the budget, so this is the analyst cost of one linked scheme.
- **Time to link:** hours from a scheme's first window to the first window in which two of its accounts share an incident; median over linked schemes.

**Rule (reported, no hypothesis):** S2 − S0 for each metric, with a paired scheme-bootstrap 95% CI. These metrics describe the value the paper claims, case assembly, in the units an analyst works in.

## P3. Protecting the alert flag

**Problem:** on LI-Medium test, S1 attack − prior TPR at 1% FPR is +0.092 for "fan-in in the top decile". S3 does not help, because the flag is never noised.

**Candidates (built and measured on Medium validation only):**

- **Flag-RR(ε):** the responder's alert bit goes through binary randomised response with ε ∈ {0.5, 1, 2, 4}, memoised per account and epoch, giving an ε-local-DP guarantee for the bit. The requester's fusion features use the noisy flag, and the stacker is refitted on validation as in A13.
- **Gated flag (τ):** the flag is answered only if the requester's own score bucket is ≥ τ ∈ {2, 3}; otherwise "no answer". Same logic as PD.
- **Gated flag-RR:** the gate at τ = 2 combined with RR at ε ∈ {1, 2}. This grid was fixed on 7 Nov, before any frontier was run.
- RR applies to the flag of **every** queried account, with or without a record, so that a record's existence does not show through. It is drawn once per account (or token) and epoch.

**Measured for each candidate on HI- and LI-Medium validation:** linked detection, its share of unprotected S1's gain, and the A2/A3 attacks with the H1c margin.

**Selection rule (fixed now):**

1. Among the candidates whose attack − prior upper bound at 1% FPR is ≤ 0.05 on every assessable target, on **both** Medium validations, choose the one with the largest mean share of unprotected S1's gain.
2. Ties go to the smaller ε, then to the ungated version.
3. If none meets the margin, **no candidate is chosen**. The frontier is reported and P3 confirms nothing.

**Rule on Large test (chosen candidate):**

- **H1c-flag:** within the margin on every assessable target.
- **Utility:** ≥ 0.80 of unprotected S1's linked gain.

Both are reported per dataset.

## P4. Adaptive token budget

**Rule (fixed now):** each bank's budget for an epoch is 2 × its largest legitimate use in the previous epoch. The first epoch uses the A16 value. A floor of the A16 value always applies.

**Evaluated by:**

- replaying the recorded legitimate token use of week-18 X1, which is label-free;
- then the P1 Large runs.

**Reported:**

- the share of legitimate requests the rule would refuse (the target is under 1%);
- the A1 re-identification and PT2 ratio (hashing ÷ OPRF, target ≥ 10) at the adaptive budget, against the frozen A16 budget.

No hypothesis is attached; it is a design result.

**Implementation note (7 Nov, no rule change).** `finmesh budget-replay` reads the saved X1 test runs (token counts and the A1 audit rows; nothing is opened). An epoch that straddles validation and test counts both partitions' use. A1 at a budget uses the audit's own formula, with the adversary using its best epoch.

**Open point for both owners, before the frozen commit.** The rule has no ceiling, and the token service cannot tell legitimate queries from an attack: a bank spending its whole budget every epoch doubles it every epoch (A16 × 2^k after k epochs), and soon tokenises every candidate, which defeats the OPRF (PT2 → 1). The replay reports this as the "ratchet". Proposed: cap at **4 × A16**, with PT2 at the cap reported as the worst case. Decided from the replay's numbers and recorded here before the freeze.

## P5. Narrative: larger local models, and select-then-template

**Candidates.** Tags are checked with `ollama pull` before freezing; a missing tag is replaced by the next listed.

| ID | Design |
| --- | --- |
| N0 | `llama3.2:3b`, the A23 prompt (the week-18 baseline) |
| N1 | `qwen2.5:7b` (instruct), the A23 prompt |
| N2 | `llama3.1:8b` (instruct), the A23 prompt |
| N3 | `qwen3:8b`, the A23 prompt, thinking disabled |
| N4 | **Select-then-template:** the best of N0–N3 chooses at most 4 evidence fields and the typology wording; fixed templates write every sentence. Faithful to the evidence by construction; the model only selects |

**Unchanged:** the A23 prompt, the checks, the retry and fallback, τ, temperature 0, JSON output, the 200-case stratified sample.

**One check added for every candidate (fixed now, from the week-18 review's main error type):** a **scope rule**. A sentence fails if it attributes to "your bank" or "the bank" a count that the evidence gives only for the linked case or for other members, or the reverse. It is reported alongside, and part of strict grounding for N0–N4.

**Development:** HI-Medium validation, the 200 week-14 cases, every candidate. The LLM judge (as in A23r) rates the same 30-case sheet for every candidate, labelled as an automated judge.

**Selection rule (fixed now):**

1. Choose the candidate with the highest strict grounding (A23 + scope).
2. Ties go to the higher H3b, then to the smaller model.
3. N4 is chosen only if its strict grounding is at least the best free-text candidate's.

**Rule on Large test (chosen candidate):** H3b ≥ 0.95, unchanged. Strict grounding and the LLM-judge faithfulness are reported.

**Hardware (to settle before freezing):**

- A 7–8 B model needs about 5 GB of memory at 4-bit. That exceeds what WSL has now (about 5.8 GB in total, shared with the system).
- **Option A:** raise WSL's memory in `%UserProfile%\.wslconfig` (`memory=12GB`), if the laptop has 16 GB or more.
- **Option B:** run Ollama on a free GPU notebook (for example Colab, T4 16 GB) for the narrative step only, with the same prompts and checks.
- Latency is reported, not judged, so either option keeps the comparison valid.

**Decision (owner, 6 Nov):** the laptop has 8 GB of RAM, so **Option B**.

1. The narrative cases (prompts, evidence, candidates, τ) are exported from the owner's machine to one file.
2. On a Colab GPU, `finmesh` runs only the model calls and the A23 + scope checks on that file. Colab needs no dataset.
3. The replies are imported and scored on the owner's machine.

Same prompts, checks, retry and fallback as a local run.

## P6. Benchmark anchor on the standard AMLworld split

This is a separate evaluation from the sealed tests. The task is transaction-level laundering classification with AMLworld's published split: transactions ordered by time, 60/20/20; minority-class F1; 5 seeds. It runs on HI-Small, LI-Small, HI-Medium and LI-Medium.

**Models:** our pooled detector (LightGBM on our 47 features, mapped to transactions by taking the maximum of the sender's and receiver's account-window scores) and a LightGBM on the transaction's own features plus ours. The decision threshold is chosen on the benchmark's validation split.

**Reported against published numbers:**

| Model | HI-Small | LI-Small | HI-Medium | LI-Medium |
| --- | --- | --- | --- | --- |
| LightGBM + graph features (Egressy et al., AAAI 2024) | 62.86 | 20.83 | 59.48 | 20.85 |
| XGBoost + graph features (Egressy et al., AAAI 2024) | 63.23 | 27.30 | 65.70 | 28.16 |
| Multi-PNA + EU (Egressy et al., AAAI 2024) | 68.16 | 33.07 | 66.48 | 36.07 |

**Rule (reported, no hypothesis):** where our detector stands among published models. Its purpose is to show the sharing gain sits on a competitive base detector, not a weak one.

**What the table compares.** The published models see every bank's transactions, so they correspond to our pooled oracle, not to one bank (S0). Our claim is the sharing gain over S0 with the same detector on both sides, so the base detector must be competitive, not best.

**Adequacy rule (fixed now):**

1. Measure our pooled detector on the benchmark's **validation** split.
2. If it is more than 5 F1 points below LightGBM + graph features on HI-Medium or LI-Medium, develop a stronger detector on validation only: XGBoost, the transaction's own features, and cycle and fan features in the style of the Graph Feature Preprocessor (Blanuša et al., 2024).
3. Run that detector as an extra track in the P1 Large confirmation (S0+, S2+, oracle+), with the same rules as H1a-L and H1b-L.
4. The week-18 results are never recomputed with it.
5. If the detector is within 5 points, nothing changes and its standing is reported.

GNNs such as Multi-PNA need a GPU and are out of scope; they are cited as published results.

**Implementation note (7 Nov, no rule change).** The benchmark split follows the benchmark code: whole days, the two boundaries whose shares are closest to 60/20/20 (smallest largest relative error), every transaction including the sparse tail our G0 window drops. It is built as a dataset of its own, `<source>-FULL`, whose G0 uses that split with 6 h windows and no gaps; labels and features come from the unchanged pipeline. Model A is trained, as the oracle is, on the train days' account-window labels; model B on the train days' transaction labels (negatives subsampled at 10% and weighted). Because the adequacy rule can add a track to the Large confirmation, **the Medium sets run before the frozen commit**; the Small sets are reported only.

## P7. Related-work positioning (writing only)

A table comparing what is shared, the privacy mechanism, the data and the evaluation discipline:

- Project Aurora (BIS Innovation Hub, 2023): collaborative analytics on synthetic payments;
- the Visa entry to the US/UK PETs challenge (arXiv 2310.04546): FL + MPC with bank flags;
- Fed-RD (arXiv 2408.01609): vertical/horizontal FL with DP;
- FinTracer (AUSTRAC, IACR ePrint 2023/649): encrypted flow tracing;
- the federated GNN on AMLworld of Zheng et al. (arXiv 2512.24487);
- Altman et al. (NeurIPS 2023) and Egressy et al. (AAAI 2024) for the data and benchmark.

None of these evaluates on a sealed, pre-registered test, which is this project's clearest methodological difference.

## Selections made on validation (7 Nov, by the rules above)

**P3, protected flag: `S1F[gate=2]`** (`docs/eval/a25/flag_selection.md`). Every candidate was within the H1c margin on every assessable target of both Medium sets. The rule took the largest mean share of plain S1's gain: 1.010 (HI 1.007, LI 1.014). Plain S1 itself missed the margin on LI-Medium validation (A3 fan-in), as it did on the week-18 test; every protected candidate passed. Attacks are measured on seed 0 only, so the margin check carries that uncertainty. The Large runs use `test-x1 --flag "S1F[gate=2]"`.

**P5, narrative: N4, select-then-template on `qwen3:8b`** (`docs/eval/a25/narrative_HI-Medium_val_*.md`).

| Candidate | Strict grounding, first replies | H3b |
| --- | --- | --- |
| N0 `llama3.2:3b` | 0.125 | 0.955 |
| N1 `qwen2.5:7b` | 0.100 | 0.965 |
| N2 `llama3.1:8b` | 0.055 | 0.990 |
| N3 `qwen3:8b` | **0.215** | 0.980 |
| N4 on N3 (`qwen3:8b`) | **0.830** | 0.985 |

1. The best free-text candidate is N3 (rule 1), so N4 is built from N3's replies.
2. N4's strict grounding (0.830) is at least N3's (0.215), so N4 is chosen (rule 3).
3. N4 built on N2's replies would score 0.985. It is reported as secondary and not chosen: the rule builds N4 on the best free-text model.

All four free-text models fail strict grounding mainly by citing more than four fields: only 13–29% of first replies cite one to four. The larger models do not fix that.

*Implementation fix before selection (7 Nov).* N4 rewrote the text from the model's first four cited fields but still checked the model's full citation list, so any reply citing more than four fields failed. N4's design is that the model selects at most four, so the check now sees the four it kept. This was found on validation, before the freeze, and fixed in code with a test.

*Known limitation, reported.* The claim checker does not read negation for cycles and treats some evidence labels as claims. For example, "max short cycles through one account: 0, no cycle" counts as an unsupported cycle claim. That accounts for most of N4's remaining strict failures (31 of 34 on N3's replies). The check is unchanged, because it is frozen for every candidate. Those cases fall back to the plain template, so the analyst still sees checked text.

**P4, adaptive budget: not adopted; the protocol keeps the frozen A16 budget** (both owners, 7 Nov; `docs/eval/a25/budget_replay_*_cap4x.md`). Replay of the week-18 test runs, seeds 0–2, validation history included:

| | HI-Medium | LI-Medium |
| --- | --- | --- |
| Legitimate requests refused, frozen A16 | 20.4–21.3% | 0–0.2% |
| Refused, adaptive (cap 4 × A16) | 12.8–13.9% (target < 1%: **missed**) | 0–0.2% (met) |
| PT2, frozen A16 → adaptive | 19.9 → 4.2 | 8.6 → 4.7 |
| PT2 after a bank spends its full budget for 2 epochs (capped) | 2.0 | 1.5 |

The rule fails on both counts. Busy test days needed more than twice the previous epoch's use, so refusals stay high on HI-Medium. Any budget large enough for them gives an attacking bank proportionally more room, so PT2 falls below 10. Reported as a negative design result: under this threat model, per-epoch metering alone cannot both serve busy days and keep re-identification low. The Large runs serve every request (A24a) and report the frozen budget's shortfall and this replay (`budget-replay --cap-factor 4`).

**P6, adequacy: triggered on HI-Medium; the stronger-detector track is added** (both owners, 7 Nov; `docs/eval/a25/benchmark_*.md`).

| Minority-class F1 (%), test | HI-Medium | LI-Medium |
| --- | --- | --- |
| A · our pooled detector (account-window LightGBM, max of the two accounts) | 42.67 ± 2.76 | 24.08 ± 2.01 |
| B · transaction LightGBM, own fields + both accounts' 47 features | **67.01 ± 2.27** | **34.34 ± 1.55** |
| LightGBM + graph features (published) | 59.48 | 20.85 |
| XGBoost + graph features (published) | 65.70 | 28.16 |
| Multi-PNA + EU (published) | 66.48 | 36.07 |

1. Model A's validation F1 was 45.03 on HI-Medium against 59.48: 14.45 points below, more than 5, so the rule is triggered. On LI-Medium it was +3.07 above (not triggered).
2. Model B, built from the rule's own ingredients (the transaction's own fields on top of our features), is above every published model on HI-Medium and above both gradient-boosting baselines on LI-Medium.
3. The gap is therefore in mapping account-window scores onto transactions, not in the features.

**The stronger-detector track (S0+, S2+, oracle+), fixed now** (`finmesh/training/txdetector.py`):

- **Detector.** Model B's design, scored per side. One row per (transaction, side held at the scoring member): the transaction's fields, the side's role, the own account's account-window features, and the counterparty's features.
  - **S0+**: one model per member on its own rows, member view. The counterparty's features are used only when the same member holds it.
  - **oracle+**: one pooled model with pooled features for both accounts.
  - Training: transaction labels of the training partition after the burn-in, with G0's evaluation mask. Negatives subsampled at 5% and weighted back; early stopping on the end of training.
- **Account-window score:** the largest side score in the window. It replaces the account-window LightGBM everywhere in the ladder (calibration, A13 alerts, records, sharing levels, stackers, the relational oracle). Nothing else changes.
- **Configurations:** S0+, S2+, oracle+ and the relational oracle+. Seeds 0–2, no audit, no sweeps, no X6. Its own experiment (`X1-plus`) and opening per dataset and seed (`test-x1 --plus`).
- **Rules, each Large dataset:**
  - **H1a-L+**: S2+ − S0+ linked detection, paired 95% CI above 0.
  - **H1b-L+**: S2+ ≥ 0.60 of the relational oracle+'s gain over S0+, if oracle+ − S0+ meets the G1 criterion.
- **Token requests:** this track's candidates differ from the current detector's, and the A16 budget was sized on the current detector's traffic. Its requests are therefore served in full on validation as well as at test (as A24a does at test), and its peak use is reported against the frozen budget.
- **Validation check before the freeze:** `finmesh plus-validation` on HI-Medium and LI-Medium, next to the current detector on the same seeds. It is reported, not tuned: the design above is fixed.

**LLM-judge ratings (reported, 7 Nov; `docs/eval/a25/narrative_judge_A25N.md`):** delivered text was faithful on the 30-case sheet in 70% (N0), 87% (N1), 97% (N2), 77% (N3) and **100% (N4, chosen)** of cases, against 33% for A23 in week 18. Of the texts the models wrote themselves, 50%, 64%, 93% and 65% were faithful.

**Still to record before the frozen commit:** the `plus-validation` results (reported).

## Order of work and sign-offs

1. **Owner signs this plan.** Then the code for P1 (Large window cut and runs), P2, P3, P4, P5 (scope rule and model switch) and P6.
2. **Validation development:** P3 frontier, P4 replay, P5 candidates. Each selection is made by its rule above and written into this file **before** step 3. The owner signs a second time: the frozen commit for the Large openings.
3. **Fresh confirmation:** HI-Large and LI-Large windows (P1, P2, P3, P4, P5), one opening per experiment, dataset and seed. P6 uses its own benchmark split: its Medium sets run in step 2 (the adequacy rule can add a track here), its Small sets at any time.
4. **Results page and the paper's tables.** Every rule here is applied mechanically; a missed rule is reported as a finding.
