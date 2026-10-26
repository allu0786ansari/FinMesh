# Sharing protocol run · HI-Medium (seed 0)

Validation windows 39–50; federation B8; every member runs S0 (local LightGBM, every feature), calibrated on the held-out end of training, and alerts at the primary budget (6,240 alerts). Requests cover the 12 windows before each alert; links use alert flags only (week 6 rule), so S1 and S2 link the same alerts by design. Total 174 s, peak memory 1,304 MB.

## Protocol

| Level | Requests | Answered: alert | Answered: record, no alert | No record | Refused | Refusal reasons | Token evaluations | Max per bank-epoch (budget 250,000) | Messages (all allowlisted) | Cross-bank links | Cross-member incidents | Seconds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S0 | 0 | 0 | 0 | 0 | 0 | — | 0 | 0 | 0 | 0 | 0 | 16.00 |
| S1 | 23,323 | 5,403 | 0 | 17,790 | 130 | rate_limited 130 | 84,675 | 11,789 | 46,678 | 5,568 | 905 | 35.90 |
| S2 | 23,323 | 5,403 | 3,907 | 13,883 | 130 | rate_limited 130 | 84,675 | 11,789 | 46,678 | 5,568 | 905 | 34.80 |

## Linked detection at the primary budget (alerts_1_per_1000_per_day)

| Level | Linked [95% CI] | Linked across members | Detected [95% CI] | Linked gain over S0 [95% CI] | p |
| --- | --- | --- | --- | --- | --- |
| S0 | 0.1742 [0.1434, 0.2051] | 0.0000 | 0.8639 [0.8330, 0.8911] | — | — |
| S1 | 0.6044 [0.5644, 0.6443] | 0.5390 | 0.8639 [0.8330, 0.8911] | 0.4301 [0.3883, 0.4737] | 0.0000 |
| S2 | 0.6044 [0.5644, 0.6443] | 0.5390 | 0.8639 [0.8330, 0.8911] | 0.4301 [0.3883, 0.4737] | 0.0000 |
| S0+pooled-link | 0.6044 [0.5644, 0.6443] | 0.5390 | 0.8639 [0.8330, 0.8911] | 0.4301 [0.3883, 0.4737] | 0.0000 |

`S0+pooled-link` links S0's alerts with the pooled rule: the most any protocol can link without changing which account-windows are alerted.

Peak memory by phase (MB): detector 1,100.70, records 1,304.20, edges 1,034.50, S0 1,196.10, S1 1,088.30, S2 1,118.80, reference 1,206.40.

## Evidence stores

| Member | Records | Autoencoder iterations | Reconstruction MSE |
| --- | --- | --- | --- |
| 0 | 9,882 | 60 | 0.1189 |
| 1 | 9,643 | 60 | 0.1245 |
| 2 | 9,084 | 60 | 0.1410 |
| 3 | 7,686 | 60 | 0.1195 |
| 4 | 8,442 | 60 | 0.1073 |
| 5 | 10,927 | 60 | 0.1320 |
| 6 | 9,176 | 60 | 0.1343 |
| 7 | 9,944 | 60 | 0.1205 |
