# X5 · privacy unit and degree cap on validation · LI-Medium

Seeds [0, 1, 2]; 50 rounds × 20 local steps. DP settings from `finmesh/schemas/dp_hparams.json` (dp-tune LI-Small): clip norm 1, expected batch 512, learning rate 0.001 (A18). Account unit: one account's bag of at most 8 windows. Degree cap: at most 16 distinct counterparties per account, features rebuilt. AUPRC pooled over validation, averaged over seeds; Poisson bootstrap over accounts shared by every configuration. Run `20261030T090742Z`; total 4,774 s, peak memory 1,488 MB.

## Non-private references

| Configuration | AUPRC [95% CI] | AUROC (mean) |
| --- | --- | --- |
| Centralised MLP, non-private | 0.0874 [0.0801, 0.0955] | 0.9736 |
| Local-only MLP, non-private | 0.0609 [0.0555, 0.0673] | 0.9696 |
| FedAvg MLP, non-private | 0.0757 [0.0683, 0.0835] | 0.9731 |
| Centralised MLP, non-private, degree cap 16 | 0.0880 [0.0805, 0.0966] | 0.9667 |

The cap alone (non-private): 0.0006 [-0.0012, 0.0021] AUPRC.

## FedAvg + DP-SGD: AUPRC by unit, features and ε

| ε | Window unit | Window unit, capped | Account unit | Account unit, capped |
| --- | --- | --- | --- | --- |
| 1.00 | 0.0275 [0.0259, 0.0293] | 0.0282 [0.0265, 0.0301] | 0.0284 [0.0269, 0.0302] | 0.0287 [0.0270, 0.0307] |
| 3.00 | 0.0311 [0.0294, 0.0332] | 0.0312 [0.0294, 0.0331] | 0.0322 [0.0305, 0.0343] | 0.0319 [0.0302, 0.0338] |
| 10.00 | 0.0332 [0.0314, 0.0354] | 0.0330 [0.0312, 0.0350] | 0.0340 [0.0322, 0.0362] | 0.0336 [0.0317, 0.0356] |

## H2a on validation (tuned DP)

Window unit, member-view features: at least 0.70 of the centralised MLP and above the local-only MLP. Judged on test.

| ε | Share of centralised [95% CI] | Minus local-only [95% CI] | Met on validation |
| --- | --- | --- | --- |
| 1 | 0.3144 [0.2838, 0.3494] | -0.0334 [-0.0393, -0.0277] | no |
| 3 | 0.3559 [0.3226, 0.3910] | -0.0298 [-0.0358, -0.0244] | no |
| 10 | 0.3795 [0.3460, 0.4161] | -0.0277 [-0.0338, -0.0226] | no |

## H2b on validation

At the same ε the account unit loses measurably more AUPRC than the window unit: the paired difference window − account has a 95% CI above 0.

| ε | Window − account [95% CI] | Account as a share of window | Met on validation |
| --- | --- | --- | --- |
| 1 | -0.0010 [-0.0011, -0.0008] | 1.04 [1.03, 1.04] | no |
| 3 | -0.0011 [-0.0013, -0.0009] | 1.03 [1.03, 1.04] | no |
| 10 | -0.0008 [-0.0010, -0.0006] | 1.03 [1.02, 1.03] | no |

## Cost of the degree cap under DP

| ε | Account unit: capped − uncapped | Window unit: capped − uncapped |
| --- | --- | --- |
| 1 | 0.0003 [-0.0000, 0.0006] | 0.0007 [0.0004, 0.0011] |
| 3 | -0.0003 [-0.0008, 0.0001] | 0.0001 [-0.0003, 0.0005] |
| 10 | -0.0004 [-0.0011, 0.0002] | -0.0001 [-0.0008, 0.0004] |

What the cap buys is in `influence_<ds>.md`: the number of other accounts' training units one account moves through its neighbours' features.
