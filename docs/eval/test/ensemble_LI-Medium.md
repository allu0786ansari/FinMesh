# X4 · stacked ensemble on test · LI-Medium

> **Sealed test (week 18).** Every model trained on the training partition; every calibration, threshold, fusion and attribution parameter fitted on validation and frozen; test scored label-free, then opened once per seed through the logged seal (`finmesh sealed-log`). Wording below that says *validation* in a column or check name refers to the frozen rule; every number is on **test**.

Base scores per seed: each member's local GBDT and local autoencoder (member view), and the neural scorers saved by X5 run `20261030T154443Z` (DP scorer: account unit, degree cap 16; dp-tune LI-Small (A19)). Stacker: A13 (per member, standardised logistic regression, C = 1), cross-fitted on the two halves of validation, on logit(GBDT), log(autoencoder error) and logit(neural). AUPRC pooled over validation, averaged over seeds [0, 1, 2], paired Poisson bootstrap over accounts. 6,978 s, peak memory 4,143 MB.

| Configuration | AUPRC [95% CI] |
| --- | --- |
| Local GBDT (raw scores) | 0.0558 [0.0486, 0.0637] |
| Stack: GBDT | 0.0597 [0.0522, 0.0680] |
| Stack: GBDT + autoencoder (local) | 0.0600 [0.0524, 0.0682] |
| DP scorer, ε = 1 alone | 0.0292 [0.0268, 0.0322] |
| Stack: local + DP scorer, ε = 1 | 0.0618 [0.0542, 0.0702] |
| DP scorer, ε = 3 alone | 0.0389 [0.0346, 0.0440] |
| Stack: local + DP scorer, ε = 3 | 0.0634 [0.0557, 0.0723] |
| DP scorer, ε = 10 alone | 0.0489 [0.0424, 0.0564] |
| Stack: local + DP scorer, ε = 10 | 0.0641 [0.0564, 0.0732] |
| FedAvg MLP, non-private alone | 0.0508 [0.0442, 0.0585] |
| Stack: local + FedAvg MLP, non-private | 0.0644 [0.0562, 0.0734] |
| Centralised MLP, non-private alone | 0.0579 [0.0501, 0.0667] |
| Stack: local + Centralised MLP, non-private | 0.0677 [0.0592, 0.0770] |

Recalibrating the GBDT per member (stack − raw): 0.0039 [0.0021, 0.0056]; adding the autoencoder: 0.0003 [-0.0000, 0.0006].

## What each federated scorer adds to the local ensemble

| Added scorer | Gain over local ensemble [95% CI] | CI above 0 |
| --- | --- | --- |
| DP scorer, ε = 1 | 0.0019 [0.0008, 0.0028] | yes |
| DP scorer, ε = 3 | 0.0035 [0.0024, 0.0046] | yes |
| DP scorer, ε = 10 | 0.0041 [0.0026, 0.0057] | yes |
| FedAvg MLP, non-private | 0.0044 [0.0025, 0.0067] | yes |
| Centralised MLP, non-private | 0.0078 [0.0055, 0.0103] | yes |

The DP scorer adds to the local ensemble from ε = 1 (smallest ε whose gain has a 95% CI above 0).
