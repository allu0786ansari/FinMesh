# X4 · stacked ensemble on validation · HI-Medium

Base scores per seed: each member's local GBDT and local autoencoder (member view), and the neural scorers saved by X5 run `20261030T134944Z` (DP scorer: account unit, degree cap 16; dp-tune HI-Small (A19)). Stacker: A13 (per member, standardised logistic regression, C = 1), cross-fitted on the two halves of validation, on logit(GBDT), log(autoencoder error) and logit(neural). AUPRC pooled over validation, averaged over seeds [0, 1, 2], paired Poisson bootstrap over accounts. 2,785 s, peak memory 2,421 MB.

| Configuration | AUPRC [95% CI] |
| --- | --- |
| Local GBDT (raw scores) | 0.3367 [0.3207, 0.3512] |
| Stack: GBDT | 0.3295 [0.3131, 0.3439] |
| Stack: GBDT + autoencoder (local) | 0.3292 [0.3129, 0.3436] |
| DP scorer, ε = 1 alone | 0.2139 [0.2028, 0.2241] |
| Stack: local + DP scorer, ε = 1 | 0.3280 [0.3129, 0.3421] |
| DP scorer, ε = 3 alone | 0.2253 [0.2138, 0.2365] |
| Stack: local + DP scorer, ε = 3 | 0.3289 [0.3139, 0.3431] |
| DP scorer, ε = 10 alone | 0.2375 [0.2253, 0.2493] |
| Stack: local + DP scorer, ε = 10 | 0.3298 [0.3150, 0.3440] |
| FedAvg MLP, non-private alone | 0.2874 [0.2723, 0.3020] |
| Stack: local + FedAvg MLP, non-private | 0.3337 [0.3171, 0.3479] |
| Centralised MLP, non-private alone | 0.3101 [0.2948, 0.3244] |
| Stack: local + Centralised MLP, non-private | 0.3397 [0.3229, 0.3538] |

Recalibrating the GBDT per member (stack − raw): -0.0072 [-0.0087, -0.0061]; adding the autoencoder: -0.0003 [-0.0007, 0.0001].

## What each federated scorer adds to the local ensemble

| Added scorer | Gain over local ensemble [95% CI] | CI above 0 |
| --- | --- | --- |
| DP scorer, ε = 1 | -0.0012 [-0.0023, -0.0000] | no |
| DP scorer, ε = 3 | -0.0003 [-0.0015, 0.0008] | no |
| DP scorer, ε = 10 | 0.0006 [-0.0008, 0.0018] | no |
| FedAvg MLP, non-private | 0.0045 [0.0025, 0.0066] | yes |
| Centralised MLP, non-private | 0.0105 [0.0078, 0.0130] | yes |

At no ε ≤ 10 does the DP scorer add to the local ensemble with a 95% CI above 0.
