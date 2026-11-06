# X5 · privacy unit and degree cap on test · LI-Medium

> **Sealed test (week 18).** Every model trained on the training partition; every calibration, threshold, fusion and attribution parameter fitted on validation and frozen; test scored label-free, then opened once per seed through the logged seal (`finmesh sealed-log`). Wording below that says *validation* in a column or check name refers to the frozen rule; every number is on **test**.

Seeds [0, 1, 2]; 50 rounds × 20 local steps. DP settings from `finmesh/schemas/dp_hparams.json` (dp-tune LI-Small (A19)): clip norm 10, expected batch 2048, learning rate 0.01, 20 local steps per round (A19). Account unit: one account's bag of at most 8 windows. Degree cap: at most 16 distinct counterparties per account, features rebuilt. AUPRC pooled over validation, averaged over seeds; Poisson bootstrap over accounts shared by every configuration. Run `20261030T154443Z`; total 8,812 s, peak memory 2,222 MB.

## Non-private references

| Configuration | AUPRC [95% CI] | AUROC (mean) |
| --- | --- | --- |
| Centralised MLP, non-private | 0.0579 [0.0501, 0.0667] | 0.9670 |
| Local-only MLP, non-private | 0.0382 [0.0337, 0.0437] | 0.9569 |
| FedAvg MLP, non-private | 0.0508 [0.0442, 0.0585] | 0.9624 |
| Centralised MLP, non-private, degree cap 16 | 0.0582 [0.0506, 0.0668] | 0.9483 |

The cap alone (non-private): 0.0003 [-0.0014, 0.0019] AUPRC.

## FedAvg + DP-SGD: AUPRC by unit, features and ε

| ε | Window unit | Window unit, capped | Account unit | Account unit, capped |
| --- | --- | --- | --- | --- |
| 1.00 | 0.0353 [0.0312, 0.0404] | 0.0348 [0.0310, 0.0398] | 0.0277 [0.0254, 0.0303] | 0.0292 [0.0268, 0.0322] |
| 3.00 | 0.0447 [0.0386, 0.0520] | 0.0437 [0.0378, 0.0509] | 0.0394 [0.0347, 0.0448] | 0.0389 [0.0346, 0.0440] |
| 10.00 | 0.0500 [0.0427, 0.0585] | 0.0518 [0.0447, 0.0601] | 0.0462 [0.0401, 0.0531] | 0.0489 [0.0424, 0.0564] |

## H2a on test (tuned DP)

Window unit, member-view features: at least 0.70 of the centralised MLP and above the local-only MLP. Decided here, on test.

| ε | Share of centralised [95% CI] | Minus local-only [95% CI] | Met on test |
| --- | --- | --- | --- |
| 1 | 0.6087 [0.5718, 0.6541] | -0.0029 [-0.0056, -0.0003] | no |
| 3 | 0.7714 [0.7274, 0.8166] | 0.0065 [0.0034, 0.0098] | yes |
| 10 | 0.8631 [0.8184, 0.9056] | 0.0118 [0.0078, 0.0158] | yes |

## H2b on test

At the same ε the account unit loses measurably more AUPRC than the window unit: the paired difference window − account has a 95% CI above 0.

| ε | Window − account [95% CI] | Account as a share of window | Met on test |
| --- | --- | --- | --- |
| 1 | 0.0076 [0.0050, 0.0111] | 0.7846 [0.7219, 0.8425] | yes |
| 3 | 0.0053 [0.0029, 0.0081] | 0.8816 [0.8391, 0.9301] | yes |
| 10 | 0.0038 [0.0018, 0.0061] | 0.9234 [0.8888, 0.9634] | yes |

## Cost of the degree cap under DP

| ε | Account unit: capped − uncapped | Window unit: capped − uncapped |
| --- | --- | --- |
| 1 | 0.0016 [0.0005, 0.0028] | -0.0004 [-0.0016, 0.0005] |
| 3 | -0.0005 [-0.0020, 0.0010] | -0.0010 [-0.0025, 0.0004] |
| 10 | 0.0027 [0.0012, 0.0042] | 0.0018 [0.0004, 0.0031] |

What the cap buys is in `influence_<ds>.md`: the number of other accounts' training units one account moves through its neighbours' features.

## Bank-partitioned versus IID (deployed setup: account unit, capped features)

The IID arm deals the same training accounts to clients at random, keeping each client's number of accounts. The gap is what the banks' different populations cost federated training.

| Configuration | Bank-partitioned | IID | IID − partitioned [95% CI] | Partitioned as a share of IID |
| --- | --- | --- | --- | --- |
| Non-private FedAvg | 0.0487 [0.0430, 0.0556] | 0.0513 [0.0449, 0.0584] | 0.0025 [0.0016, 0.0035] | 0.9506 [0.9372, 0.9665] |
| DP, ε = 1 | 0.0292 [0.0268, 0.0322] | 0.0292 [0.0268, 0.0321] | -0.0001 [-0.0003, 0.0001] | 1.00 [0.9974, 1.01] |
| DP, ε = 3 | 0.0389 [0.0346, 0.0440] | 0.0386 [0.0345, 0.0435] | -0.0002 [-0.0007, 0.0001] | 1.01 [0.9971, 1.02] |
| DP, ε = 10 | 0.0489 [0.0424, 0.0564] | 0.0504 [0.0437, 0.0582] | 0.0015 [0.0009, 0.0022] | 0.9695 [0.9592, 0.9816] |
