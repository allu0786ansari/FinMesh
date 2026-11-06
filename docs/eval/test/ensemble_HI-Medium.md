# X4 · stacked ensemble on test · HI-Medium

> **Sealed test (week 18).** Every model trained on the training partition; every calibration, threshold, fusion and attribution parameter fitted on validation and frozen; test scored label-free, then opened once per seed through the logged seal (`finmesh sealed-log`). Wording below that says *validation* in a column or check name refers to the frozen rule; every number is on **test**.

Base scores per seed: each member's local GBDT and local autoencoder (member view), and the neural scorers saved by X5 run `20261030T134944Z` (DP scorer: account unit, degree cap 16; dp-tune HI-Small (A19)). Stacker: A13 (per member, standardised logistic regression, C = 1), cross-fitted on the two halves of validation, on logit(GBDT), log(autoencoder error) and logit(neural). AUPRC pooled over validation, averaged over seeds [0, 1, 2], paired Poisson bootstrap over accounts. 7,459 s, peak memory 4,179 MB.

| Configuration | AUPRC [95% CI] |
| --- | --- |
| Local GBDT (raw scores) | 0.2005 [0.1884, 0.2130] |
| Stack: GBDT | 0.2033 [0.1911, 0.2161] |
| Stack: GBDT + autoencoder (local) | 0.2038 [0.1915, 0.2168] |
| DP scorer, ε = 1 alone | 0.1312 [0.1222, 0.1406] |
| Stack: local + DP scorer, ε = 1 | 0.2077 [0.1956, 0.2204] |
| DP scorer, ε = 3 alone | 0.1389 [0.1293, 0.1485] |
| Stack: local + DP scorer, ε = 3 | 0.2079 [0.1958, 0.2206] |
| DP scorer, ε = 10 alone | 0.1454 [0.1356, 0.1555] |
| Stack: local + DP scorer, ε = 10 | 0.2087 [0.1967, 0.2214] |
| FedAvg MLP, non-private alone | 0.1715 [0.1605, 0.1840] |
| Stack: local + FedAvg MLP, non-private | 0.2199 [0.2072, 0.2323] |
| Centralised MLP, non-private alone | 0.1861 [0.1746, 0.1983] |
| Stack: local + Centralised MLP, non-private | 0.2271 [0.2140, 0.2398] |

Recalibrating the GBDT per member (stack − raw): 0.0027 [0.0015, 0.0039]; adding the autoencoder: 0.0006 [0.0002, 0.0008].

## What each federated scorer adds to the local ensemble

| Added scorer | Gain over local ensemble [95% CI] | CI above 0 |
| --- | --- | --- |
| DP scorer, ε = 1 | 0.0039 [0.0029, 0.0048] | yes |
| DP scorer, ε = 3 | 0.0041 [0.0031, 0.0050] | yes |
| DP scorer, ε = 10 | 0.0049 [0.0037, 0.0059] | yes |
| FedAvg MLP, non-private | 0.0161 [0.0142, 0.0179] | yes |
| Centralised MLP, non-private | 0.0232 [0.0206, 0.0256] | yes |

The DP scorer adds to the local ensemble from ε = 1 (smallest ε whose gain has a 95% CI above 0).
