# X5 · privacy unit and degree cap on test · HI-Medium

> **Sealed test (week 18).** Every model trained on the training partition; every calibration, threshold, fusion and attribution parameter fitted on validation and frozen; test scored label-free, then opened once per seed through the logged seal (`finmesh sealed-log`). Wording below that says *validation* in a column or check name refers to the frozen rule; every number is on **test**.

Seeds [0, 1, 2]; 50 rounds × 20 local steps. DP settings from `finmesh/schemas/dp_hparams.json` (dp-tune HI-Small (A19)): clip norm 10, expected batch 512, learning rate 0.01, 20 local steps per round (A19). Account unit: one account's bag of at most 8 windows. Degree cap: at most 16 distinct counterparties per account, features rebuilt. AUPRC pooled over validation, averaged over seeds; Poisson bootstrap over accounts shared by every configuration. Run `20261030T134944Z`; total 8,626 s, peak memory 2,184 MB.

## Non-private references

| Configuration | AUPRC [95% CI] | AUROC (mean) |
| --- | --- | --- |
| Centralised MLP, non-private | 0.1861 [0.1746, 0.1983] | 0.9726 |
| Local-only MLP, non-private | 0.1451 [0.1345, 0.1559] | 0.9666 |
| FedAvg MLP, non-private | 0.1715 [0.1605, 0.1840] | 0.9697 |
| Centralised MLP, non-private, degree cap 16 | 0.1762 [0.1646, 0.1887] | 0.9570 |

The cap alone (non-private): -0.0099 [-0.0144, -0.0052] AUPRC.

## FedAvg + DP-SGD: AUPRC by unit, features and ε

| ε | Window unit | Window unit, capped | Account unit | Account unit, capped |
| --- | --- | --- | --- | --- |
| 1.00 | 0.1032 [0.0953, 0.1117] | 0.1053 [0.0970, 0.1142] | 0.1313 [0.1221, 0.1409] | 0.1312 [0.1222, 0.1406] |
| 3.00 | 0.1294 [0.1201, 0.1398] | 0.1205 [0.1116, 0.1300] | 0.1362 [0.1266, 0.1463] | 0.1389 [0.1293, 0.1485] |
| 10.00 | 0.1367 [0.1269, 0.1473] | 0.1346 [0.1249, 0.1448] | 0.1443 [0.1340, 0.1550] | 0.1454 [0.1356, 0.1555] |

## H2a on test (tuned DP)

Window unit, member-view features: at least 0.70 of the centralised MLP and above the local-only MLP. Decided here, on test.

| ε | Share of centralised [95% CI] | Minus local-only [95% CI] | Met on test |
| --- | --- | --- | --- |
| 1 | 0.5545 [0.5295, 0.5799] | -0.0418 [-0.0485, -0.0353] | no |
| 3 | 0.6954 [0.6667, 0.7235] | -0.0156 [-0.0216, -0.0095] | no |
| 10 | 0.7346 [0.7065, 0.7621] | -0.0083 [-0.0138, -0.0029] | no |

## H2b on test

At the same ε the account unit loses measurably more AUPRC than the window unit: the paired difference window − account has a 95% CI above 0.

| ε | Window − account [95% CI] | Account as a share of window | Met on test |
| --- | --- | --- | --- |
| 1 | -0.0281 [-0.0326, -0.0238] | 1.27 [1.23, 1.32] | no |
| 3 | -0.0068 [-0.0103, -0.0033] | 1.05 [1.02, 1.08] | no |
| 10 | -0.0076 [-0.0111, -0.0041] | 1.06 [1.03, 1.08] | no |

## Cost of the degree cap under DP

| ε | Account unit: capped − uncapped | Window unit: capped − uncapped |
| --- | --- | --- |
| 1 | -0.0001 [-0.0030, 0.0025] | 0.0021 [-0.0010, 0.0050] |
| 3 | 0.0027 [-0.0005, 0.0056] | -0.0089 [-0.0123, -0.0057] |
| 10 | 0.0011 [-0.0021, 0.0040] | -0.0021 [-0.0053, 0.0011] |

What the cap buys is in `influence_<ds>.md`: the number of other accounts' training units one account moves through its neighbours' features.

## Bank-partitioned versus IID (deployed setup: account unit, capped features)

The IID arm deals the same training accounts to clients at random, keeping each client's number of accounts. The gap is what the banks' different populations cost federated training.

| Configuration | Bank-partitioned | IID | IID − partitioned [95% CI] | Partitioned as a share of IID |
| --- | --- | --- | --- | --- |
| Non-private FedAvg | 0.1709 [0.1596, 0.1833] | 0.1662 [0.1549, 0.1785] | -0.0047 [-0.0056, -0.0038] | 1.03 [1.02, 1.03] |
| DP, ε = 1 | 0.1312 [0.1222, 0.1406] | 0.1284 [0.1194, 0.1375] | -0.0029 [-0.0034, -0.0022] | 1.02 [1.02, 1.03] |
| DP, ε = 3 | 0.1389 [0.1293, 0.1485] | 0.1371 [0.1276, 0.1468] | -0.0017 [-0.0024, -0.0010] | 1.01 [1.01, 1.02] |
| DP, ε = 10 | 0.1454 [0.1356, 0.1555] | 0.1428 [0.1331, 0.1528] | -0.0025 [-0.0033, -0.0018] | 1.02 [1.01, 1.02] |
