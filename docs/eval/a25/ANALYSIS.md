# A25 analysis: what the Large confirmation adds to the paper

Sources:
- the Large results page, `docs/eval/a25/RESULTS_LARGE.md`;
- the run pages in `docs/eval/test/*Large-W16*`;
- the week-18 page, `docs/eval/test/RESULTS.md`;
- the validation development in `docs/eval/a25/` and the plan, `docs/protocol/improvement_plan_A25.md`.

Every Large number below comes from a sealed test opened once per experiment, dataset and seed, under the re-signed frozen commit (`c10fea8`; the HI-Large main run under `177b77d`, with the same code path).

## 1. Bottom line

The central claim replicates on fresh, never-opened data from a different period of AMLworld, in both regimes:

- Minimised evidence sharing (S2) raises linked scheme detection by 0.47 (HI) and 0.38 (LI) over local-only detection.
- S2 recovers 0.92 and 0.64 of what a fully pooled relational oracle achieves.
- The gain survives removing the suspected artefact features, and it survives a base detector that matches published state of the art.

The two week-18 weaknesses that A25 targeted are now resolved on fresh data:
- the alert-flag leak (H1c on LI);
- narrative grounding (H3b).

Two things still miss and must be reported:
- typology attribution (H3a);
- the OPRF re-identification ratio (PT2) at the frozen token budget.

## 2. Scorecard: week 18 (Medium) vs A25 (Large)

| Claim | HI-Medium (wk 18) | LI-Medium (wk 18) | HI-Large (A25) | LI-Large (A25) |
| --- | --- | --- | --- | --- |
| **H1a** S2 − S0 linked detection | +0.566 [0.529, 0.606] ✔ | +0.549 [0.449, 0.634] ✔ | **+0.471 [0.433, 0.508] ✔** | **+0.383 [0.289, 0.478] ✔** |
| **H1b** share of relational oracle's gain (≥ 0.60) | 0.98 ✔ | 0.79 ✔ | **0.92 [0.87, 0.97] ✔** | **0.64 [0.52, 0.77] ✔** |
| H1a without artefact features | — | — | **+0.438 ✔** | **+0.210 ✔** |
| H1a with the stronger detector (S0+ → S2+) | — | — | **+0.433 ✔** | **+0.355 ✔** |
| H1b with the stronger detector | — | — | **0.92 ✔** | 0.49 ✘ |
| **H1c** privacy margin, plain S1/S3 | ✔ | ✘ (fan-in) | ✔ | ✘ (fan-in, same mechanism) |
| H1c, **protected flag S1F[gate=2]** | — | — | ✔ (keeps 1.00 of S1's gain) | **✔ (keeps 0.93 of S1's gain)** |
| **H1d** PD ≥ 0.80 of S2's gain at < 0.5 disclosure | ✔ (uninformative) | ✔ | ✔ (uninformative: S1 ≈ 0.95) | ✔ at τ = 2 (0.81, 20% disclosure) and τ = 4 (0.81, ≈ 0% disclosure) |
| **H3a** attribution S2 > S0, majority, rules | ✔ | ✘ | ✘ | ✘ |
| **H3b** narrative grounding ≥ 0.95 | 0.86 ✘ | 0.92 ✘ | **1.00 ✔** (N4) | **0.95 ✔** (N4, 61 cases) |
| Token budget A16 holds on test | ✘ (18.8% over) | ✔ | ✔ | ✔ |
| PT2 hashing ÷ OPRF ≥ 10 | 19.9 ✔ | 8.7 ✘ | 8.1 ✘ | 9.3 ✘ |

## 3. What now strengthens the paper

1. **Replication on fresh data.** Most collaborative-AML and federated-AML papers report one split, tuned and reported on the same data. Here the headline is decided on a pre-registered sealed test, then replicated on two further sealed windows from another period, with every opening logged. Across six datasets (HI/LI Small, Medium and Large) the H1a gain is positive with its CI above 0 every time.
2. **The gain is not an artefact.** Without the seven payment-format shares and `self_tx`, the gain is still +0.44 (HI-Large) and +0.21 (LI-Large). LI depends more on those features: S0 falls to 0.007. Say so plainly; it is a finding about AMLworld's LI data.
3. **The base detector is competitive.** On AMLworld's own published split, our features in a transaction model:
   - beat both published gradient-boosting baselines on all four sets: HI-Small 64.3, LI-Small 35.0, HI-Medium 67.0, LI-Medium 34.3 F1;
   - beat the best published GNN (Multi-PNA) on LI-Small (35.0 vs 33.1) and HI-Medium (67.0 vs 66.5);
   - trail it on HI-Small (68.2) and LI-Medium (36.1). With that detector as the base (S0+), sharing still adds +0.43 and +0.36 on the Large tests. This answers "the gain only exists because the local detector is weak."
4. **A privacy leak found, fixed and confirmed on fresh data.**
   - Week 18 showed that sharing a bare alert flag lets a peer infer which accounts have high fan-in (LI-Medium).
   - The same leak reappears on LI-Large: plain S1 attack − prior is 0.043 [0.031, 0.059].
   - The protected flag chosen on validation by a frozen rule closes it on test: 0.004 [0.000, 0.007] on LI-Large. It keeps 93–100% of the flag's detection value.
   - This is a complete, pre-registered find → fix → confirm cycle, which reviewers rarely see.
5. **Analyst workload falls sharply** (case quality, P2). With S2, an analyst needs **18 alerts per linked scheme instead of 153** (HI-Large), and **140 instead of 944** (LI-Large).
   - Cases are more complete: 0.77 vs 0.47 of the scheme's accounts on HI, 0.73 vs 0.48 on LI.
   - Fragmentation nearly halves: 1.05 vs 1.51 cases per scheme.
   - This is the number practitioners care about, and it belongs in the abstract.
6. **Progressive disclosure is informative on LI-Large.** PD at τ = 4 reaches 0.81 of S2's gain with almost no records disclosed (S1 alone is just under the 0.80 cut-off by the rule's estimate). On HI it is uninformative, as in week 18, because S1 alone gets 0.95.
7. **Narrative: a design that is grounded by construction.**
   - Larger free-text models did not fix grounding: strict grounding was 0.06–0.22 on validation.
   - Select-then-template (N4) meets H3b on both Large tests.
   - An automated judge rated its validation texts faithful in 30 of 30 cases, against 10 of 30 for week 18's delivered texts.

## 4. What must be reported as limits

- **H3a (typology attribution) does not replicate.** The S2 attributor beats the rules baseline on HI-Large (+0.045) but not S0's attributor or the majority class. Present attribution as exploratory. The paper's contribution is detection and linking, not typology.
- **PT2 misses on both Large windows (8.1, 9.3) and on LI-Medium (8.7).** The OPRF reduces token re-identification about 8–9× relative to hashing, short of the pre-registered 10×. The adaptive budget (P4) makes this worse (PT2 2.6–3.2) and does not reduce refusals on Large, so it was correctly not adopted. Report OPRF as a large but not complete mitigation; per-epoch metering alone cannot both serve busy days and keep re-identification low. That is itself a useful negative result for system designers.
- **LI-Large is small.** It has 78 multi-member test schemes, as LI-Medium did, so its intervals are wide.
  - H1b on LI-Large holds at 0.64, but its CI reaches 0.52.
  - H3b rests on 61 cases (lower bound 0.865).
  - Report intervals, not just verdicts.
- **H1b-L+ misses on LI-Large (0.49).** With the stronger detector, the pooled oracle+ is very strong on LI (0.76 linked; relational 0.79). S2+ keeps its absolute gain but not its share. The plain reading: the better the pooled model, the more a minimised-evidence protocol leaves on the table.
- **Synthetic data only.** AMLworld is the field's standard benchmark, but external validity to real bank data is unproven. State it in the limitations and in the title framing ("on AMLworld").
- **No human expert review.** The narrative faithfulness judgement is by one automated judge, not blind and not independent of the design. Present it as automated, with its limits, as the A23r and A25 judge pages do.
- **Amendments.** A24, A24a, A24b, A25, A25s and A25a are all logged with reasons, and none changed a result after an opening that affected it. A25a fixed a run that stopped before opening. Put the amendment table in the appendix; it is evidence of discipline, not a weakness, if shown in full.

## 5. How to frame the paper

**Claims the evidence supports:**

1. Sharing minimised, tokenised evidence between banks raises cross-bank scheme detection several-fold over local-only monitoring (0.06 → 0.53 linked detection on HI-Large). It recovers most of a fully pooled model's gain, on pre-registered sealed tests, replicated on fresh data.
2. The gain holds without suspected dataset artefacts and on a state-of-the-art base detector.
3. Naive flag sharing leaks a sensitive attribute. A gated flag removes the leak while keeping its value, confirmed on fresh data.
4. Shared evidence makes investigations far cheaper: 7–8× fewer alerts per linked scheme, and more complete cases.
5. Grounded case narratives are achievable with small local models only when the model selects evidence and templates write the text.

**Claims to avoid:**

- any claim about typology attribution beyond "exploratory";
- "OPRF prevents re-identification" (it reduces it about 8–9×);
- any claim about real-bank performance;
- "LLM narratives are faithful" for free text.

**Suggested headline numbers for the abstract:** HI-Large linked detection 0.063 → 0.534 (+0.47), 0.92 of the pooled relational oracle; 8× fewer alerts per linked scheme; base detector above both published gradient-boosting baselines on all four standard benchmark sets, and above the best GNN on two; alert-flag leak closed by gating at no detection cost.

## 6. Venue fit

The strongest form of this work is an evaluation-rigorous applied paper. The pre-registered sealed test with fresh replication is the methodological contribution; the detection, workload and privacy results are the substantive ones.

- **Most natural:** ACM ICAIF (AI in Finance); the KDD Applied Data Science track; AAAI or IJCAI special tracks on AI for social impact. Each values applied impact plus rigorous evaluation.
- **Privacy venues (PoPETs, the Financial Cryptography workshops):** possible, but the PT2 miss and the lack of a formal end-to-end privacy proof will be questioned. Frame the privacy part as an empirical leakage audit.
- **Top ML main tracks:** less natural without a new learning method. A datasets-and-benchmarks or evaluation track fits better there.

No venue can be guaranteed. The paper now has what reviewers usually find missing in this area: held-out confirmation, artefact checks, a benchmark anchor, an honest privacy audit and practical metrics.

## 7. Before submission

1. **P7 related work** (writing): the comparison table of Project Aurora, the Visa PETs entry, Fed-RD, FinTracer and the federated GNN on AMLworld.
2. **Paper figures:**
   - the sharing ladder (S0 → S1 → S2 → oracle) on the four datasets;
   - the privacy frontier, with the protected flag;
   - case quality as alerts per linked scheme;
   - the benchmark table.
3. **Cosmetic fixes in the generated pages:**
   - The H1c row's description reads as a pass even when the verdict is "no"; it should name the failing target (A3 fan-in).
   - The audit page truncates the configuration name `S1F[gate=2]`.
4. ~~The Small benchmark runs~~ (done 9 Nov: the benchmark table has all four published columns).
5. **Optional, but it strengthens the narrative claim:** a two-person rating of the N4 test texts. The two-rater scorer already exists.
