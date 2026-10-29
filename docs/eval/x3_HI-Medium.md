# X3 · evidence-channel privacy on validation · HI-Medium

Seeds [0, 1, 2]; primary budget alerts_1_per_1000_per_day; primary fusion stacker, fitted on evidence released through the same mechanism. S3: every record field but the time bucket and alert flag through k-ary randomised response at ε / 20 per field, memoised per record, at most ε = 8 per account and epoch (over budget: the S1 answer). PD: the S1 answer, plus the S2 record when the requester's score bucket is at least τ.

![S3 and PD sweeps](x3_HI-Medium.png)

## S3: recall versus ε

| ε per record | Linked [95% CI] | Gain over S0 | Share of relational-oracle gain | Records withheld (budget), mean per seed | Max ε spent on one account |
| --- | --- | --- | --- | --- | --- |
| 0.5000 | 0.7260 [0.6939, 0.7605] | 0.5523 [0.5124, 0.5929] | 0.9641 [0.9208, 1.01] | 0.0000 | 5.00 |
| 1.00 | 0.7320 [0.6987, 0.7659] | 0.5584 [0.5184, 0.5983] | 0.9747 [0.9316, 1.02] | 13.00 | 8.00 |
| 2.00 | 0.7381 [0.7072, 0.7719] | 0.5644 [0.5257, 0.6038] | 0.9852 [0.9417, 1.03] | 510.67 | 8.00 |
| 4.00 | 0.7344 [0.7023, 0.7683] | 0.5608 [0.5221, 0.6013] | 0.9789 [0.9321, 1.02] | 1,899.00 | 8.00 |
| 8.00 | 0.7393 [0.7060, 0.7725] | 0.5656 [0.5281, 0.6068] | 0.9873 [0.9448, 1.03] | 6,351.33 | 8.00 |

## PD: recall versus disclosure volume (H1d)

H1d: at least 0.80 of S2's gain over S0 with records disclosed on fewer than half as many accounts as S2. Judged on test; validation shown here.

| τ (requester bucket) | Linked [95% CI] | Share of S2 gain [95% CI] | Accounts disclosed, share of S2 | Accounts disclosed (mean) | H1d met on validation |
| --- | --- | --- | --- | --- | --- |
| 2.00 | 0.7350 [0.7042, 0.7677] | 0.9989 [0.9774, 1.02] | 0.2955 | 12,557.67 | yes |
| 3.00 | 0.7284 [0.6951, 0.7629] | 0.9871 [0.9613, 1.01] | 0.1359 | 5,783.00 | yes |
| 4.00 | 0.7084 [0.6751, 0.7417] | 0.9516 [0.9231, 0.9794] | 0.0905 | 3,851.33 | yes |

Reference: S1, which discloses no record, reaches 0.9839 [0.9605, 1.01] of S2's gain. When this is itself at least 0.80, H1d holds for any τ and says little about disclosure; the informative comparison is then PD against S1.
