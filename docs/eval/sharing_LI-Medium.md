# Sharing protocol run · LI-Medium (seed 0)

Validation windows 39–50; federation B8; every member runs S0 (local LightGBM, every feature), calibrated on the held-out end of training, and alerts at the primary budget (6,144 alerts). Requests cover the 12 windows before each alert; links use alert flags only (week 6 rule), so S1 and S2 link the same alerts by design. Total 135 s, peak memory 1,281 MB.

## Protocol

| Level | Requests | Answered: alert | Answered: record, no alert | No record | Refused | Refusal reasons | Token evaluations | Max per bank-epoch (budget 250,000) | Messages (all allowlisted) | Cross-bank links | Cross-member incidents | Seconds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S0 | 0 | 0 | 0 | 0 | 0 | — | 0 | 0 | 0 | 0 | 0 | 14.40 |
| S1 | 23,955 | 1,371 | 0 | 22,514 | 70 | rate_limited 70 | 86,775 | 14,955 | 47,942 | 1,379 | 461 | 35.50 |
| S2 | 23,955 | 1,371 | 6,178 | 16,336 | 70 | rate_limited 70 | 86,775 | 14,955 | 47,942 | 1,379 | 461 | 33.60 |

## Linked detection at the primary budget (alerts_1_per_1000_per_day)

| Level | Linked [95% CI] | Linked across members | Detected [95% CI] | Linked gain over S0 [95% CI] | p |
| --- | --- | --- | --- | --- | --- |
| S0 | 0.1505 [0.0860, 0.2153] | 0.0000 | 0.8387 [0.7527, 0.9140] | — | — |
| S1 | 0.5161 [0.4086, 0.6129] | 0.4731 | 0.8387 [0.7527, 0.9140] | 0.3656 [0.2688, 0.4624] | 0.0000 |
| S2 | 0.5161 [0.4086, 0.6129] | 0.4731 | 0.8387 [0.7527, 0.9140] | 0.3656 [0.2688, 0.4624] | 0.0000 |
| S0+pooled-link | 0.5161 [0.4086, 0.6129] | 0.4731 | 0.8387 [0.7527, 0.9140] | 0.3656 [0.2688, 0.4624] | 0.0000 |

`S0+pooled-link` links S0's alerts with the pooled rule: the most any protocol can link without changing which account-windows are alerted.

Peak memory by phase (MB): detector 1,069.80, records 1,281.40, edges 1,045.50, S0 1,227.00, S1 1,056.30, S2 1,056.30, reference 1,132.20.

## Evidence stores

| Member | Records | Autoencoder iterations | Reconstruction MSE |
| --- | --- | --- | --- |
| 0 | 12,573 | 60 | 0.1218 |
| 1 | 9,552 | 60 | 0.1290 |
| 2 | 7,821 | 60 | 0.1428 |
| 3 | 6,508 | 60 | 0.1240 |
| 4 | 8,396 | 60 | 0.1287 |
| 5 | 8,308 | 60 | 0.1369 |
| 6 | 9,591 | 60 | 0.1279 |
| 7 | 5,974 | 60 | 0.1434 |
