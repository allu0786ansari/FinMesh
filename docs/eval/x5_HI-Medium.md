# X5 · privacy unit and degree cap on validation · HI-Medium

Seeds [0, 1, 2]; 50 rounds × 20 local steps. DP settings from `finmesh/schemas/dp_hparams.json` (dp-tune HI-Small): clip norm 1, expected batch 512, learning rate 0.001 (A18). Account unit: one account's bag of at most 8 windows. Degree cap: at most 16 distinct counterparties per account, features rebuilt. AUPRC pooled over validation, averaged over seeds; Poisson bootstrap over accounts shared by every configuration. Run `20261030T073000Z`; total 5,265 s, peak memory 1,487 MB.

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
| 1.00 | 0.1005 [0.0933, 0.1076] | 0.1032 [0.0956, 0.1112] | 0.0866 [0.0814, 0.0916] | 0.0907 [0.0843, 0.0972] |
| 3.00 | 0.1319 [0.1217, 0.1411] | 0.1369 [0.1274, 0.1471] | 0.1322 [0.1241, 0.1409] | 0.1444 [0.1340, 0.1552] |
| 10.00 | 0.1532 [0.1421, 0.1633] | 0.1635 [0.1526, 0.1745] | 0.1712 [0.1600, 0.1818] | 0.1840 [0.1721, 0.1959] |

## H2a on validation (tuned DP)

Window unit, member-view features: at least 0.70 of the centralised MLP and above the local-only MLP. Judged on test.

| ε | Share of centralised [95% CI] | Minus local-only [95% CI] | Met on validation |
| --- | --- | --- | --- |
| 1 | 0.3243 [0.3071, 0.3407] | -0.1518 [-0.1612, -0.1401] | no |
| 3 | 0.4255 [0.4020, 0.4463] | -0.1204 [-0.1304, -0.1095] | no |
| 10 | 0.4942 [0.4702, 0.5163] | -0.0991 [-0.1095, -0.0898] | no |

## H2b on validation

At the same ε the account unit loses measurably more AUPRC than the window unit: the paired difference window − account has a 95% CI above 0.

| ε | Window − account [95% CI] | Account as a share of window | Met on validation |
| --- | --- | --- | --- |
| 1 | 0.0139 [0.0113, 0.0169] | 0.8615 [0.8406, 0.8846] | yes |
| 3 | -0.0003 [-0.0032, 0.0021] | 1.00 [0.9843, 1.02] | no |
| 10 | -0.0179 [-0.0214, -0.0148] | 1.12 [1.10, 1.14] | no |

## Cost of the degree cap under DP

| ε | Account unit: capped − uncapped | Window unit: capped − uncapped |
| --- | --- | --- |
| 1 | 0.0040 [0.0025, 0.0062] | 0.0026 [0.0003, 0.0054] |
| 3 | 0.0122 [0.0090, 0.0158] | 0.0050 [0.0017, 0.0086] |
| 10 | 0.0128 [0.0095, 0.0173] | 0.0102 [0.0067, 0.0148] |

What the cap buys is in `influence_<ds>.md`: the number of other accounts' training units one account moves through its neighbours' features.
