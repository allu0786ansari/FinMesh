# Verification record for `main.tex`

Each factual statement in the draft and its source in the repository. Result pages are under `docs/eval/test` (week-18 and Large runs), `docs/eval/a25` (A25 development and results) and `docs/gates` (G0/G1). Code paths are under `finmesh/`. Rounding in the text is half-up to the digits shown. Checked 9 Nov 2026; statements added in the 12 Nov revision (`REVISION_PLAN.md`) are in the last section.

## System (Section III)

| Statement | Source |
| --- | --- |
| Visibility: a bank sees transactions with one end at its accounts, incl. the counterparty's account and bank | `docs/protocol/preregistration.md` §1; `finmesh/data/visibility.py` |
| Threat model: honest-but-curious peer and token service; no collusion, poisoning, compromised hosts | `docs/proposal/FinMesh_Proposal_v2.md` §10 |
| 6-h windows; LightGBM per bank; 47 features in four families; current window + 72 h | preregistration §1, §6; `finmesh/schemas/features_v3.json`; `finmesh/models/gbdt.py` |
| Fixed alert count per window (1 per 1,000 accounts per day) | preregistration §3 (A10) |
| Local incidents: accounts transacted directly within 72 h | preregistration §4; `finmesh/fusion/local.py` |
| OPRF: RFC 9497, mode 0, ristretto255-SHA512 | `finmesh/matching/oprf.py` docstring |
| Seven-day epochs | `finmesh/matching/tokens.py` (`EPOCH_WINDOWS = 28`, 6 h each) |
| Per-epoch budget = 2 × largest legitimate validation use | preregistration A16; `finmesh/schemas/token_budgets.json` |
| Shared-key hashing as audit control only | `finmesh/matching/tokens.py` (`HashTokenClient`) |
| Query trigger: calibrated probability ≥ 0.01 or alerted; counterparties within 72 h | preregistration §6a (A13) |
| S1 = alert flag + time bucket | proposal §8.4; `finmesh/sharing/node.py` |
| S2 record: probability bucket, top-3 autoencoder deviations with direction and magnitude bucket, counters fan_out, fan_in, tx_out, tx_in, amt_out, amt_in, pass_through, cross_bank_share, new_cp_share, delay_min_h | `finmesh/schemas/evidence_v1.json` |
| S3: k-ary RR on all fields but time and flag; ε ∈ {0.5,1,2,4,8}; cap 8 per account and epoch | preregistration §6b (A15), A16 |
| S4: 8-dimensional embedding | `finmesh/fusion/triage.py` (`EMBED_DIM`); preregistration §6a |
| PD: S1 + S2 record when requester bucket ≥ τ, τ ∈ {2,3,4} | preregistration §6b |
| Gated flag: flag only when requester bucket ≥ 2 | `finmesh/sharing/node.py` (`_protected_flag`); `docs/eval/a25/flag_selection.md` |
| Stacker inputs (own logit; requests sent, refused, alert answers; inbound; record count, max/sum probability, max deviation, fan-in, fan-out, pass-through) | `finmesh/fusion/triage.py` (`COMMON`, `S2_EXTRA`) |
| Logistic stacker, cross-fitted on the validation halves; same budget; pooled 72-h linking | preregistration §6a |
| Oracle; relational oracle (pooled score + counterparties' pooled scores, stacker) as H1b ceiling | preregistration §6, §6a (A14) |
| Attributor; JSON narrative with typology and field checks; one retry; template fallback; N4 selects ≤ 4 fields | preregistration §6d–6g; `finmesh/attribution/narrative.py`, `narrative_cases.py` |

## Fig. 1 (architecture) and the request sentences in Section III

Fig. 1 updates the proposal's workflow diagram (`docs/proposal/workflow.png`) to the system that was built and evaluated. Changes from that diagram: two banks drawn as requester and responder with the bank boundary, the response policy shown as the evaluated levels (S1, S1F, S2, S3, PD) rather than "S1 by default, escalate", the gated flag added, and three boxes left out. The federated DP scorer is left out because gate G3 kept detectors local; the privacy ledger and analyst approval belong to the demo path, which the paper does not evaluate.

| Element | Source |
| --- | --- |
| Token service: OPRF RFC 9497 ristretto255-SHA512, 7-day epoch key, per-bank per-epoch budget | `finmesh/matching/oprf.py`, `tokens.py`; preregistration A16 |
| Blinded IDs ↔ tokens between requester and token service | `finmesh/sharing/simulate.py` (A tokenises b through the token service) |
| Each bank tokenises its own accounts to index its records | `finmesh/sharing/node.py` (token index) |
| Local detector: LightGBM, 47 features, calibrated score | as Section III-B rows above |
| Query: score ≥ 0.01 or alerted; counterparties at B within 72 h | preregistration §6a (A13) |
| Request fields: token, time range, purpose, hop limit, requester bucket; signed | `finmesh/sharing/messages.py` (`EvidenceRequest`) |
| Signed by a request issuer (Ed25519) whose public key nodes hold | `finmesh/sharing/requests.py` (`RequestIssuer`) |
| Guard refuses bad signature, expired, replayed (nonce), undeclared purpose, spent hop limit, more than 20 answers per token and epoch | `finmesh/sharing/requests.py` (`RequestGuard`, `RATE_PER_TOKEN = 20`, `EXPIRY_WINDOWS = 1`); used in every run via `simulate.py` |
| Evidence store: own alerts and minimised records | `finmesh/sharing/node.py` |
| Response policy S1, S1F, S2, S3 RR(ε), PD(τ); S4 reference not drawn | `finmesh/sharing/node.py` |
| Only requests and responses cross between banks | `finmesh/sharing/messages.py` (`ALLOWLIST`, `Bus`) |
| Fusion stacker; fixed alert budget; cross-bank linking 72 h; typology; N4 | as Section III-E/F rows above |
| Leakage audit: B as honest-but-curious peer attacking what it receives | preregistration §6b (A15); `docs/eval/test/audit_*.md` |

## Evaluation method (Section IV)

| Statement | Source |
| --- | --- |
| HI and LI AMLworld; four sealed tests | `docs/eval/test/RESULTS.md`; `docs/eval/a25/RESULTS_LARGE.md` |
| Medium dense period 16 days; Large = last 16 days of dense period | `docs/gates/G0_evidence_HI-Medium.md` (16 dense days); `finmesh/data/window.py` |
| 60/20/20 windows, one-window gaps; B8 | preregistration §1 |
| Table II counts (transactions in window, laundering rows, schemes, cross-member test schemes) | `docs/gates/G0_evidence_<set>.md` (partition rows, "Schemes:", "test schemes touch") |
| Labels, masking, incidental rule (≥ 20 legs, < 10%) | preregistration §2 (A9) |
| Detected / linked within 72 h | preregistration §4 |
| G1: oracle − S0 = 0.508 [0.465, 0.550]; any-alert S0 0.864, oracle 0.886 | preregistration §9 |
| Registration, provisional thresholds revised once at G1, then frozen | preregistration header and §5 |
| SHA-256 digest; one opening per experiment, dataset and seed; repeats logged | preregistration §6h (A24); `finmesh/eval/sealed.py` |
| A25 rules and selections (gated flag 1.01; N4 on qwen3:8b; adequacy gap 14.5) | `docs/protocol/improvement_plan_A25.md` ("Selections made on validation"); `docs/eval/a25/flag_selection.md`; `docs/eval/a25/benchmark_HI-Medium.md` |
| Frozen commit signed; three tracks per Large window | improvement plan line 4; `docs/eval/test/x1_*Large-W16*.md` |
| Seeds 5/3; 1,000 bootstrap replicates; Holm across sharing configurations | preregistration §6h, §7 |
| Audit A1–A3, attacker and baseline, margin 0.05 | preregistration §6b (A15); `docs/eval/test/audit_*.md` |

## Results (Section V)

| Statement | Source |
| --- | --- |
| S0 0.063–0.136; S2 0.702, 0.657, 0.534, 0.450 | `docs/eval/test/x1_<set>.md`, "Linked detection per configuration" |
| Gains with CIs; Holm; random-alert linked 0.000 | `RESULTS.md`, `RESULTS_LARGE.md` (H1a rows) |
| Recovery 0.98, 0.79, 0.92, 0.64; LI-Large CI to 0.52 | same pages (H1b rows) |
| S1 0.516 on HI-Large; pooled oracle 0.434 | `docs/eval/test/x1_HI-Large-W16.md` |
| Without artefacts: gain 0.438, 0.210; LI-Large S1 0.054, S2 0.217 | `RESULTS_LARGE.md` (H1a-L-noart); `docs/eval/test/x1_LI-Large-W16_noart.md` |
| Benchmark claims (both GBDT baselines on all four; best GNN on two) | `docs/eval/a25/benchmark_table.md` |
| S0+ → S2+ gains 0.433, 0.355; oracle+ 0.764; recovery 0.49 | `RESULTS_LARGE.md` (H1a-L+, H1b-L+); `docs/eval/test/x1_LI-Large-W16_plus.md` |
| Fan-in advantage 0.092 (LI-Medium), 0.043 [0.031, 0.059] (LI-Large); gated 0.004 [0.000, 0.007]; keeps 1.00 / 0.93; S2/S4 0.73–0.74 | `docs/eval/test/audit_<set>.md` (A3 fan-in); `RESULTS_LARGE.md` (protected-flag rows) |
| "A plausible reason ..." (flag informative about payers in LI) | interpretation, stated as such; not tested |
| PD τ = 4: 0.95 / 0.81 at 3% / < 1% disclosure; S1 ≈ 0.95 of S2 on HI-Large | `RESULTS_LARGE.md` (H1d-L rows) |
| Hashing 0.39, OPRF 0.049 (HI-Large); PT2 8.1, 9.3, 8.7, 19.9 | `docs/eval/test/audit_<set>.md` ("Pooled:" line) |
| Test token use within budget on both Large windows | `RESULTS_LARGE.md` (token-budget rows) |
| Adaptive budget: refusals far above 1%; ratio 2.6–3.2; not adopted | `docs/eval/a25/budget_replay_*_cap4x.md`; improvement plan (P4 decision) |
| Completeness 0.77 vs 0.47; fragmentation 1.05 vs 1.51; alerts 153 → 18, 944 → 140 | `RESULTS_LARGE.md` (case-quality rows); definitions in `finmesh/eval/schemes.py` |
| H3a met on HI-Medium only | `RESULTS.md`, `RESULTS_LARGE.md` (H3a rows) |
| H3b 0.86 / 0.92 (week 18); strict 0.06–0.22 for four models; N4 1.00 / 0.95; judge 30/30 vs 21–29 | `RESULTS.md`; `docs/eval/a25/narrative_*_val_*.md`; `narrative_*_test_qwen3-8b_N4.md`; `narrative_judge_A25N.md` |

## Limitations and conclusion (Sections VI–VII)

| Statement | Source |
| --- | --- |
| 78 and 91 cross-member test schemes (LI) | `docs/gates/G0_evidence_LI-Large-W16.md`, `G0_evidence_LI-Medium.md` |
| Federated DP scorer met target on LI-Medium, not HI-Medium | `RESULTS.md` (H2a rows) |
| A24a, A25a before openings; A24b report-only after an opening | `docs/proposal/CHANGES.md` |
| "Several times as many schemes" (0.063 → 0.534 is 8.5×; 0.136 → 0.702 is 5.2×) | as above |

## Related work (Section II, Table I)

Every claim about another paper is sourced in `docs/paper/related_work.md`, with the links used to check it.

## Added in the 12 Nov revision

| Statement | Source |
| --- | --- |
| FATF encourages information sharing within data-protection rules | [fatf2021stocktake], [fatf2022partnering] (checked 12 Nov; links in `REVISION_PLAN.md`) |
| "Primary tests" = HI-/LI-Medium sealed tests (week 18); "replication tests" = HI-/LI-Large windows (A25) | `docs/eval/test/RESULTS.md`; `docs/eval/a25/RESULTS_LARGE.md` |
| Fed-RD reports peak test performance without a separate validation split (at least one study) | `docs/paper/related_work.md` (Khan et al. row) |
| OPRF lineage; attack-based privacy risk; leakage between development and test data | [freedman2005keyword], [yeom2018privacy], [kapoor2023leakage] |
| Token service learns the number of queries per bank, not their content | `finmesh/matching/tokens.py` (per-bank, per-epoch log of counts; blinded points) |
| Probability buckets: five, edges 0.01, 0.05, 0.2, 0.5; bucket 2 ⇔ p ≥ 0.05 | `finmesh/schemas/evidence_v1.json`; `finmesh/sharing/evidence.py` (`bucket`, `searchsorted` right) |
| S3: at most ε = 8 per account and epoch, summed over releases | `finmesh/sharing/ldp.py` (`EPSILON_CAP = 8.0`) |
| Registered model settings fixed in advance, not tuned on validation | `docs/protocol/preregistration.md` §6 heading |
| All amendments but one before the results they concerned (A24b after an opening, no score changed) | `docs/proposal/CHANGES.md` |
| All runs on one 8 GB laptop | owner's machine (8 GB RAM, WSL); `docs/proposal/FinMesh_Proposal_v2.md` risk table; run logs |
| G1: payment-format shares and self-transfers strongest in every baseline model | `docs/gates/G1.md` (item 3) |
| HI-Medium primary test: legitimate token use over budget in 2 of 16 bank-epochs, 18.8% of requests | `docs/eval/test/RESULTS.md` (token-budget row) |
| Replication budgets sized per window from validation traffic | `docs/protocol/improvement_plan_A25.md` ("Token budget, sized before any test") |
| N4 strict grounding 0.82 (HI-Large), 0.56 (LI-Large) | `RESULTS_LARGE.md` (H3b rows) |
| Limitations: PT2 8.1/9.3/8.7 vs 10; adaptive budget 2.6–3.2; H1b-L+ 0.49; federation B8 | `audit_*.md`; `budget_replay_*_cap4x.md`; `RESULTS_LARGE.md`; `preregistration.md` §1 |
| `finmesh paper-assets` rebuilds Figs. 2–5 and Tables I–VI from the committed pages without data | tested 12 Nov in a clean clone: tables byte-identical, figures pixel-identical (PDFs now byte-identical too: no creation date) |
