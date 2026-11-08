# Related work (A25 P7)

Table: `docs/paper/static/tab_related.tex` (Table VI in the draft). References: `docs/paper/references.bib`. Every entry was checked against its primary source on 8–9 Nov 2026 (links below); nothing was filled in from memory.

## Draft text for the paper (to edit)

**Collaborative detection across institutions.** Money-laundering schemes are split across banks, so each bank sees a fragment. Three families of work let institutions detect such schemes together:

- **Federated learning.** Banks exchange model updates rather than data. Suzumura et al. [suzumura2019] proposed federated graph learning across banks. Zheng et al. [zheng2025] train a federated graph network on country-level subgraphs of AMLworld.
- **The US/UK PETs Prize.** Its financial-crime track produced systems that bring a bank's private account flags into a payment hub's model. Arora et al. [arora2023] use MPC and federated learning. Abadi et al. [abadi2024starlit] use private set intersection with secure federated learning. Khan et al. [khan2024fedrd] use differential privacy with secure summation.
- **Secure computation and supervisory analytics.** van Egmond et al. [vanegmond2024] propagate risk scores across banks under MPC. FinTracer [brand2023fintracer] traces money flows under homomorphic encryption at national scale. Project Aurora [bis2023aurora] compared siloed, national and cross-border collaborative analysis on synthetic payments.

**What differs here.** We share *evidence*, not models: a minimised record about a counterparty, keyed by a pseudonymous token that only the holding bank can resolve. We then measure what that evidence leaks with explicit attacks, rather than relying on a mechanism's guarantee alone. Two points distinguish the evaluation:

1. None of the works above reports results on a pre-registered, sealed test. Several select models or report peak performance on the same split they report on.
2. None replicates on data that was never opened during development. We decide every claim on a sealed test, then confirm it on two further sealed windows, with every opening logged.

**Benchmarks.** AMLworld [altman2023] provides synthetic transactions with laundering labels and typologies. On it, multigraph GNNs [egressy2024] and subgraph features with gradient boosting [blanusa2024] set the transaction-level state of the art. Our detector is anchored against those published numbers (Table IV).

## Sources

| Work | Source | Notes used in the table |
| --- | --- | --- |
| Suzumura et al. 2019 | [arXiv:1909.12946](https://arxiv.org/abs/1909.12946) | NeurIPS 2019 workshop (non-archival). Federated learning on simulated FCA TechSprint data, six banks. DP/MPC proposed, not evaluated. |
| Arora et al. 2023 | [arXiv:2310.04546](https://arxiv.org/abs/2310.04546) | PETs Prize entry. Federated learning + MPC (OT, secret sharing), noise without a formal DP claim. AUPRC on synthetic payments. |
| Abadi et al. 2024 (Starlit) | [IACR ePrint 2024/090](https://eprint.iacr.org/2024/090) | PSI + secure federated learning, with a security proof. Synthetic data. |
| Khan et al. 2024 (Fed-RD) | [arXiv:2408.01609](https://arxiv.org/abs/2408.01609) | Vertical + horizontal federated learning, DP with secure summation. PETs Prize (SWIFT) and AMLSim data. Peak test AUPRC reported, with no validation split described. |
| van Egmond et al. 2024 | [IACR ePrint 2024/065](https://eprint.iacr.org/2024/065) (FC 2024); [ERCIM News 126](https://ercim-news.ercim.eu/en126/special/privacy-preserving-collaborative-money-laundering-detection) | Secure risk propagation under MPC. Data from one Dutch bank. Precision 15% → 40% at 20% recall. |
| Brand et al. 2023 (FinTracer) | [IACR ePrint 2023/649](https://eprint.iacr.org/2023/649) | Flow tracing under homomorphic encryption. Timing at full deployment size; no detection metrics. |
| BIS Innovation Hub 2023 (Project Aurora) | [BIS report](https://www.bis.org/publications/project-aurora-power-data-technology-and-collaboration-combat-money-laundering-across-institutions-and-borders) | Synthetic data; siloed vs national vs cross-border collaborative analysis with PETs. |
| Zheng et al. 2025 | [arXiv:2512.24487](https://arxiv.org/abs/2512.24487) | Federated GNN on AMLworld HI-Small country subgraphs, 5% train / 95% test, no formal privacy guarantee. |
| Altman et al. 2023 | [NeurIPS 2023 D&B](https://proceedings.neurips.cc/paper_files/paper/2023/hash/5f38404edff6f3f642d6fa5892479c42-Abstract.html) | The AMLworld data. |
| Egressy et al. 2024 | [AAAI 2024](https://ojs.aaai.org/index.php/AAAI/article/view/29069) | Multi-GNN; the published benchmark numbers. |
| Blanuša et al. 2024 | [arXiv:2402.08593](https://arxiv.org/abs/2402.08593) (ICAIF '24, DOI 10.1145/3677052.3698674) | Graph Feature Preprocessor. |

The PETs Prize financial-crime winners (STARLIT; University of Cambridge; Featurespace) are listed on the [UKRI page](https://ukri.org/blog/privacy-enhancing-technologies-pets-prize-challenges-winners). Of these, only Starlit has a public paper we could verify.
