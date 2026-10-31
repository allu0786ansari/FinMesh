# X4 · stacked ensemble on validation · LI-Medium

Base scores per seed: each member's local GBDT and local autoencoder (member view), and the neural scorers saved by X5 run `20261030T154443Z` (DP scorer: account unit, degree cap 16; dp-tune LI-Small (A19)). Stacker: A13 (per member, standardised logistic regression, C = 1), cross-fitted on the two halves of validation, on logit(GBDT), log(autoencoder error) and logit(neural). AUPRC pooled over validation, averaged over seeds [0, 1, 2], paired Poisson bootstrap over accounts. 2,536 s, peak memory 2,463 MB.

| Configuration | AUPRC [95% CI] |
| --- | --- |
| Local GBDT (raw scores) | 0.0846 [0.0774, 0.0927] |
| Stack: GBDT | 0.0901 [0.0827, 0.0985] |
| Stack: GBDT + autoencoder (local) | 0.0899 [0.0825, 0.0984] |
| DP scorer, ε = 1 alone | 0.0426 [0.0399, 0.0459] |
| Stack: local + DP scorer, ε = 1 | 0.0889 [0.0811, 0.0973] |
| DP scorer, ε = 3 alone | 0.0571 [0.0519, 0.0627] |
| Stack: local + DP scorer, ε = 3 | 0.0917 [0.0836, 0.0997] |
| DP scorer, ε = 10 alone | 0.0799 [0.0730, 0.0889] |
| Stack: local + DP scorer, ε = 10 | 0.0957 [0.0874, 0.1047] |
| FedAvg MLP, non-private alone | 0.0757 [0.0683, 0.0835] |
| Stack: local + FedAvg MLP, non-private | 0.0924 [0.0849, 0.1002] |
| Centralised MLP, non-private alone | 0.0874 [0.0801, 0.0955] |
| Stack: local + Centralised MLP, non-private | 0.0969 [0.0883, 0.1058] |

Recalibrating the GBDT per member (stack − raw): 0.0055 [0.0035, 0.0070]; adding the autoencoder: -0.0002 [-0.0006, 0.0002].

## What each federated scorer adds to the local ensemble

| Added scorer | Gain over local ensemble [95% CI] | CI above 0 |
| --- | --- | --- |
| DP scorer, ε = 1 | -0.0010 [-0.0027, 0.0004] | no |
| DP scorer, ε = 3 | 0.0018 [0.0002, 0.0030] | yes |
| DP scorer, ε = 10 | 0.0058 [0.0039, 0.0072] | yes |
| FedAvg MLP, non-private | 0.0025 [-0.0002, 0.0050] | no |
| Centralised MLP, non-private | 0.0070 [0.0047, 0.0092] | yes |

The DP scorer adds to the local ensemble from ε = 3 (smallest ε whose gain has a 95% CI above 0).
