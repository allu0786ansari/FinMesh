# X5 · privacy unit and degree cap on validation · HI-Medium

Seeds [0, 1, 2]; 50 rounds × 20 local steps. DP settings from `finmesh/schemas/dp_hparams.json` (dp-tune HI-Small (A19)): clip norm 10, expected batch 512, learning rate 0.01, 20 local steps per round (A19). Account unit: one account's bag of at most 8 windows. Degree cap: at most 16 distinct counterparties per account, features rebuilt. AUPRC pooled over validation, averaged over seeds; Poisson bootstrap over accounts shared by every configuration. Run `20261030T134944Z`; total 6,896 s, peak memory 1,590 MB.

## Non-private references

| Configuration | AUPRC [95% CI] | AUROC (mean) |
| --- | --- | --- |
| Centralised MLP, non-private | 0.3101 [0.2948, 0.3244] | 0.9823 |
| Local-only MLP, non-private | 0.2524 [0.2370, 0.2664] | 0.9788 |
| FedAvg MLP, non-private | 0.2874 [0.2723, 0.3020] | 0.9807 |
| Centralised MLP, non-private, degree cap 16 | 0.2904 [0.2752, 0.3078] | 0.9733 |

The cap alone (non-private): -0.0197 [-0.0241, -0.0151] AUPRC.

## FedAvg + DP-SGD: AUPRC by unit, features and ε

| ε | Window unit | Window unit, capped | Account unit | Account unit, capped |
| --- | --- | --- | --- | --- |
| 1.00 | 0.2061 [0.1920, 0.2175] | 0.2007 [0.1889, 0.2134] | 0.2224 [0.2113, 0.2327] | 0.2139 [0.2028, 0.2241] |
| 3.00 | 0.2291 [0.2146, 0.2408] | 0.2153 [0.2027, 0.2283] | 0.2343 [0.2227, 0.2458] | 0.2253 [0.2138, 0.2365] |
| 10.00 | 0.2433 [0.2284, 0.2556] | 0.2290 [0.2161, 0.2425] | 0.2479 [0.2355, 0.2588] | 0.2375 [0.2253, 0.2493] |

## H2a on validation (tuned DP)

Window unit, member-view features: at least 0.70 of the centralised MLP and above the local-only MLP. Judged on test.

| ε | Share of centralised [95% CI] | Minus local-only [95% CI] | Met on validation |
| --- | --- | --- | --- |
| 1 | 0.6647 [0.6413, 0.6842] | -0.0463 [-0.0543, -0.0389] | no |
| 3 | 0.7389 [0.7168, 0.7573] | -0.0233 [-0.0303, -0.0164] | no |
| 10 | 0.7847 [0.7666, 0.8037] | -0.0090 [-0.0154, -0.0023] | no |

## H2b on validation

At the same ε the account unit loses measurably more AUPRC than the window unit: the paired difference window − account has a 95% CI above 0.

| ε | Window − account [95% CI] | Account as a share of window | Met on validation |
| --- | --- | --- | --- |
| 1 | -0.0163 [-0.0218, -0.0114] | 1.08 [1.05, 1.11] | no |
| 3 | -0.0052 [-0.0099, -0.0009] | 1.02 [1.00, 1.04] | no |
| 10 | -0.0045 [-0.0090, -0.0007] | 1.02 [1.00, 1.04] | no |

## Cost of the degree cap under DP

| ε | Account unit: capped − uncapped | Window unit: capped − uncapped |
| --- | --- | --- |
| 1 | -0.0085 [-0.0118, -0.0045] | -0.0054 [-0.0091, 0.0002] |
| 3 | -0.0090 [-0.0123, -0.0047] | -0.0138 [-0.0177, -0.0084] |
| 10 | -0.0104 [-0.0140, -0.0059] | -0.0143 [-0.0185, -0.0096] |

What the cap buys is in `influence_<ds>.md`: the number of other accounts' training units one account moves through its neighbours' features.

## Bank-partitioned versus IID (deployed setup: account unit, capped features)

The IID arm deals the same training accounts to clients at random, keeping each client's number of accounts. The gap is what the banks' different populations cost federated training.

| Configuration | Bank-partitioned | IID | IID − partitioned [95% CI] | Partitioned as a share of IID |
| --- | --- | --- | --- | --- |
| Non-private FedAvg | 0.2743 [0.2593, 0.2899] | 0.2709 [0.2559, 0.2867] | -0.0034 [-0.0046, -0.0024] | 1.01 [1.01, 1.02] |
| DP, ε = 1 | 0.2139 [0.2028, 0.2241] | 0.2087 [0.1974, 0.2189] | -0.0052 [-0.0060, -0.0045] | 1.03 [1.02, 1.03] |
| DP, ε = 3 | 0.2253 [0.2138, 0.2365] | 0.2215 [0.2099, 0.2321] | -0.0039 [-0.0047, -0.0031] | 1.02 [1.01, 1.02] |
| DP, ε = 10 | 0.2375 [0.2253, 0.2493] | 0.2310 [0.2194, 0.2426] | -0.0065 [-0.0074, -0.0058] | 1.03 [1.02, 1.03] |
