# X5 · privacy unit and degree cap on validation · LI-Medium

Seeds [0, 1, 2]; 50 rounds × 20 local steps. DP settings from `finmesh/schemas/dp_hparams.json` (dp-tune LI-Small (A19)): clip norm 10, expected batch 2048, learning rate 0.01, 20 local steps per round (A19). Account unit: one account's bag of at most 8 windows. Degree cap: at most 16 distinct counterparties per account, features rebuilt. AUPRC pooled over validation, averaged over seeds; Poisson bootstrap over accounts shared by every configuration. Run `20261030T154443Z`; total 20,650 s, peak memory 1,682 MB.

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
| 1.00 | 0.0550 [0.0504, 0.0616] | 0.0525 [0.0480, 0.0575] | 0.0436 [0.0403, 0.0468] | 0.0426 [0.0399, 0.0459] |
| 3.00 | 0.0705 [0.0639, 0.0790] | 0.0658 [0.0595, 0.0743] | 0.0610 [0.0557, 0.0674] | 0.0571 [0.0519, 0.0627] |
| 10.00 | 0.0835 [0.0762, 0.0919] | 0.0824 [0.0749, 0.0903] | 0.0791 [0.0724, 0.0873] | 0.0799 [0.0730, 0.0889] |

## H2a on validation (tuned DP)

Window unit, member-view features: at least 0.70 of the centralised MLP and above the local-only MLP. Judged on test.

| ε | Share of centralised [95% CI] | Minus local-only [95% CI] | Met on validation |
| --- | --- | --- | --- |
| 1 | 0.6291 [0.5992, 0.6629] | -0.0059 [-0.0090, -0.0034] | no |
| 3 | 0.8072 [0.7752, 0.8384] | 0.0096 [0.0064, 0.0129] | yes |
| 10 | 0.9555 [0.9297, 0.9794] | 0.0226 [0.0192, 0.0269] | yes |

## H2b on validation

At the same ε the account unit loses measurably more AUPRC than the window unit: the paired difference window − account has a 95% CI above 0.

| ε | Window − account [95% CI] | Account as a share of window | Met on validation |
| --- | --- | --- | --- |
| 1 | 0.0114 [0.0083, 0.0148] | 0.7931 [0.7547, 0.8402] | yes |
| 3 | 0.0096 [0.0070, 0.0125] | 0.8642 [0.8354, 0.8939] | yes |
| 10 | 0.0044 [0.0029, 0.0059] | 0.9475 [0.9306, 0.9647] | yes |

## Cost of the degree cap under DP

| ε | Account unit: capped − uncapped | Window unit: capped − uncapped |
| --- | --- | --- |
| 1 | -0.0010 [-0.0023, 0.0004] | -0.0025 [-0.0038, -0.0012] |
| 3 | -0.0039 [-0.0055, -0.0021] | -0.0047 [-0.0064, -0.0031] |
| 10 | 0.0008 [-0.0011, 0.0027] | -0.0011 [-0.0028, 0.0002] |

What the cap buys is in `influence_<ds>.md`: the number of other accounts' training units one account moves through its neighbours' features.

## Bank-partitioned versus IID (deployed setup: account unit, capped features)

The IID arm deals the same training accounts to clients at random, keeping each client's number of accounts. The gap is what the banks' different populations cost federated training.

| Configuration | Bank-partitioned | IID | IID − partitioned [95% CI] | Partitioned as a share of IID |
| --- | --- | --- | --- | --- |
| Non-private FedAvg | 0.0710 [0.0637, 0.0788] | 0.0752 [0.0680, 0.0835] | 0.0042 [0.0032, 0.0054] | 0.9440 [0.9322, 0.9563] |
| DP, ε = 1 | 0.0426 [0.0399, 0.0459] | 0.0425 [0.0398, 0.0457] | -0.0001 [-0.0003, 0.0001] | 1.00 [0.9986, 1.01] |
| DP, ε = 3 | 0.0571 [0.0519, 0.0627] | 0.0566 [0.0516, 0.0624] | -0.0005 [-0.0010, -0.0002] | 1.01 [1.00, 1.02] |
| DP, ε = 10 | 0.0799 [0.0730, 0.0889] | 0.0830 [0.0759, 0.0916] | 0.0031 [0.0024, 0.0038] | 0.9629 [0.9547, 0.9707] |
