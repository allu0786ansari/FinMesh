# Literature matrix

One row per work cited in the proposal, organised by the role it plays in the argument. Columns follow the week-1 plan: setting, data, mechanism, privacy unit, attack evaluated, result. **Status** tracks reading: `summary` = written from the proposal and prior knowledge, needs a check against the paper; `read` = checked against the full text; `n/a` = tool or standard, cited for method only.

Rule for later weeks: any number quoted in the paper must come from a row marked `read`.

## 1. Collaboration-level studies (the "sharing helps" baseline we build on)

| Work | Setting and data | Sharing mechanism | Privacy unit | Attack evaluated | Result relevant to FinMesh | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Altman et al. 2023, AMLworld (NeurIPS D&B) | Synthetic multi-bank world; HI/LI × Small/Medium/Large | Private graph + private model vs shared graph + shared model, per bank | None | None | Sharing data and models gives clearly higher minority-class F1 than isolation; this is our S0-vs-oracle reference | summary |
| BIS Innovation Hub 2023, Project Aurora | Synthetic domestic and cross-border payments | Siloed, national and cross-border views; centralised, decentralised and hybrid collaborative analysis | Not formalised | Not reported as attacks | Collaborative analysis detects more laundering networks than siloed rules; utility only | summary |
| Swift 2025 press release | Federated trials with 13 banks, synthetic data | Federated learning | Not stated | None | Detection reported about twice as effective as single-institution models | summary |
| UK–US PETs Prize 2023, Track A | Synthetic SWIFT transactions + partner-bank account flags | Privacy-preserving federated learning (many entrant designs) | Varies by entrant | Red-team phase (verify scope) | Shows the problem framing and that PPFL is feasible; no common sharing-granularity ladder | summary |

## 2. Federated and DP detection

| Work | Setting and data | Sharing mechanism | Privacy unit | Attack evaluated | Result relevant to FinMesh | Status |
| --- | --- | --- | --- | --- | --- | --- |
| DPxFin 2026 (arXiv:2603.19314) | AML dataset, MLP, IID and non-IID clients | FL with reputation-weighted adaptive DP noise | Record / update level | Tabular leakage motivation (verify which attack) | Better accuracy–privacy trade-off than fixed-noise DP, modest gains | summary |
| Privacy-Preserving Federated Fraud Detection 2026 (arXiv:2603.13617) | Multi-bank fraud, NVFlare, FedAvg | FL with sample-level DP | Sample | (verify) | Near-centralised F1 (0.903 reported) | summary |
| Kato et al. 2024, ULDP-FL | Cross-silo FL | FL | User-level across silos | — | Route to customer-level DP when one user spans silos; we cite it for the account vs customer distinction | summary |
| Abadi et al. 2016 | — | DP-SGD | Record | — | Method | n/a |
| Mironov 2017 | — | Rényi DP accounting | — | — | Method (our accountant) | n/a |
| McMahan et al. 2017; Li et al. 2020 | — | FedAvg; FedProx | — | — | Methods | n/a |

## 3. Cryptographic collaboration

| Work | Setting and data | Sharing mechanism | Privacy unit | Attack evaluated | Result relevant to FinMesh | Status |
| --- | --- | --- | --- | --- | --- | --- |
| IACR ePrint 2024/065, secure risk propagation | Cross-bank AML | MPC over risk scores propagated through the payment graph | Cryptographic (inputs hidden) | Security proof, not empirical leakage | Fixed single mechanism; we re-implement plain score propagation as a utility baseline | summary |
| Tian et al. 2025 (WWW), collaborative AML | AlipayECB + synthetic data | LSH + Bloom filters to detect cross-institution laundering subgroups | Graph structure hidden | (verify) | Effective cross-institution subgroup detection; one mechanism, no ladder | summary |
| FHE graph ML for collaborative AML 2024 (arXiv:2411.02926) | Balanced subsets of AMLworld HI-Small (370 pattern groups) | Fully homomorphic encryption | Cryptographic | — | Feasible but on heavily reduced data; we cite it for the 370-scheme count to verify at G0 | summary |

## 4. Matching, evidence and leakage

| Work | Setting and data | Mechanism | Privacy unit | Attack evaluated | Result relevant to FinMesh | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Davidson et al. 2023, RFC 9497 | — | OPRF over prime-order groups | — | — | Our token service | n/a |
| Wang et al. 2017 (USENIX Security) | — | Local DP frequency oracles (k-RR, OUE, ...) | Per report | — | Basis for S3 randomised response and debiasing | n/a |
| Shokri, Strobel and Zick 2021 | Model explanations | Feature attributions | — | Membership inference from explanations | Explanations leak; motivates auditing evidence records | summary |

## 5. Detection architecture (supporting choices)

| Work | Setting and data | Method | Result relevant to FinMesh | Status |
| --- | --- | --- | --- | --- |
| Blanuša et al. 2024, Graph Feature Preprocessor | AMLworld | Subgraph features + GBDT | Beats standard GNNs on minority F1, fast on CPU; our primary detector design | summary |
| Egressy et al. 2024, Multi-GNN | AMLworld | GIN + edge features, reverse MP, ego IDs, ports | Optional offline comparator | summary |
| arXiv:2112.07508, AML alert optimisation with graphs | Real bank data | ML triage after rules | About 80% fewer false positives, over 90% true positives kept; motivates the triage stacker | summary |
| Krutikov et al. 2024 (Booking.com) | Payments fraud | Tabular transformers vs GBDT | Transformers won an A/B test; keeps the neural arm honest | summary |
| Nubank 2025, nuFormer | Transaction sequences | Transformer representations | Needed tabular-specific parts to match GBDT | summary |
| Revolut and NVIDIA 2026, PRAGMA | Per-user sequences | Foundation model | Reported 47.1% worse on AML F0.5; why we keep relational features | summary |
| NVIDIA AI Blueprint | Fraud | GNN embeddings + XGBoost | Industrial reference | summary |

## 6. LLMs and agents in AML

| Work | Setting | Method | Gap FinMesh addresses | Status |
| --- | --- | --- | --- | --- |
| Naik et al. 2025, Co-Investigator AI | Single institution | Agentic SAR narrative drafting | No cross-bank setting; no grounding measure against a supervised attributor | summary |

## 7. Evaluation practice

| Work | Topic | Lesson applied | Status |
| --- | --- | --- | --- |
| Hayat 2025 | Data leakage in fraud-detection evaluation | Sealed test, label guard, temporal splits | summary |
| Kim et al. 2022; Tatbul et al. 2018 | Time-series anomaly evaluation | Avoid point-adjust inflation; event-level metrics | summary |
| Dal Pozzolo et al. 2015 | Delayed labels | Out of scope (10-day data); cited as future work | summary |

## To add while reading (week 2 onward)

- Federated graph learning for AML across banks (search: "federated graph neural network anti-money laundering cross-bank").
- Membership-inference evaluation at low FPR (LiRA, Carlini et al. 2022) for attack A5.
- LDP debiasing for downstream classifiers, for fitting fusion on S3 evidence.
- PSI-based customer matching in financial consortia (comparison point for OPRF matching).
