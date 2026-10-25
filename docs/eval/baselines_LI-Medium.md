# Baselines · LI-Medium (seed 0)

Federation B8; validation windows 39–50. Training windows 12–37 (burn-in before 12); windows 33–37 held out for early stopping and FPR thresholds. Label: primary (amendment A9: incidental positives masked). Primary operating point **alerts_1_per_1000_per_day** (A10); schemes count as detected within 12 windows of their first. S0 links alerts locally; the oracle links across members. Total 510 s, peak memory 1,706 MB.

## Validation at the primary budget (alerts_1_per_1000_per_day)

| Scorer | AUPRC [95% CI] | AUROC | Precision | Window recall | Detected [95% CI] | Random detected | Linked [95% CI] | Random linked | Linked across members | Median TTD h |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Oracle (pooled data, full graph) | 0.1199 [0.1111, 0.1308] | 0.9758 | 0.1169 | 0.1555 | 0.9140 [0.8495, 0.9677] | 0.0113 | 0.6882 [0.5914, 0.7849] | 0.0000 | 0.6344 | 0.0000 |
| S0 local GBDT, all features | 0.0765 [0.0685, 0.0852] | 0.9660 | 0.1003 | 0.1360 | 0.8387 [0.7527, 0.9140] | 0.0113 | 0.1505 [0.0860, 0.2153] | 0.0000 | 0.0000 | 0.0000 |
| S0 local GBDT, behaviour only | 0.0642 [0.0581, 0.0725] | 0.9201 | 0.0903 | 0.1239 | 0.8387 [0.7634, 0.9140] | 0.0113 | 0.1505 [0.0860, 0.2258] | 0.0000 | 0.0000 | 0.0000 |
| Isolation Forest (local) | 0.0064 [0.0059, 0.0070] | 0.7937 | 0.0269 | 0.0378 | 0.2151 [0.1398, 0.2903] | 0.0113 | 0.0215 [0.0000, 0.0538] | 0.0000 | 0.0000 | 21.00 |
| PCA reconstruction (local) | 0.0040 [0.0037, 0.0044] | 0.6184 | 0.0126 | 0.0178 | 0.0323 [0.0000, 0.0753] | 0.0113 | 0.0000 [0.0000, 0.0000] | 0.0000 | 0.0000 | 0.0000 |
| Activity (legs in window) | 0.0016 [0.0015, 0.0017] | 0.4025 | 0.0140 | 0.0197 | 0.0108 [0.0000, 0.0323] | 0.0113 | 0.0000 [0.0000, 0.0000] | 0.0000 | 0.0000 | 0.0000 |
| Random | 0.0013 [0.0012, 0.0014] | 0.5063 | 0.0010 | 0.0014 | 0.0000 [0.0000, 0.0000] | 0.0113 | 0.0000 [0.0000, 0.0000] | 0.0000 | 0.0000 | — |

Validation prevalence 0.0013; schemes evaluated 93.

## Gate G1 and PT4b comparisons (paired, same schemes and accounts)

| Difference | Linked detection | p (Holm) | Any-alert detection | p (Holm) | AUPRC | p |
| --- | --- | --- | --- | --- | --- | --- |
| oracle - S0-BG | 0.5376 [0.4409, 0.6344] | 0.0000 | 0.0753 [0.0215, 0.1290] | 0.0060 | 0.0434 [0.0368, 0.0486] | 0.0000 |
| S0-BG - S0-B | 0.0000 [-0.0323, 0.0323] | 1.00 | 0.0000 [-0.0753, 0.0753] | 1.00 | 0.0123 [0.0062, 0.0179] | 0.0000 |
| S0-BG - random | 0.1505 [0.0860, 0.2153] | 0.0000 | 0.8387 [0.7527, 0.9140] | 0.0000 | 0.0752 [0.0672, 0.0839] | 0.0000 |

## Secondary operating points (FPR budgets, thresholds from the held-out training windows)

| Scorer | Budget | Alerts | False alerts /1000 acc /day | Max member FPR | Precision | Detected | Linked |
| --- | --- | --- | --- | --- | --- | --- | --- |
| oracle | fpr_0.001 | 3,844 | 0.4627 | 0.0010 | 0.1521 | 0.8710 [0.8065, 0.9355] | 0.6129 [0.5161, 0.7097] |
| oracle | fpr_0.0001 | 605 | 0.0116 | 0.0000 | 0.7517 | 0.6774 [0.5806, 0.7742] | 0.2581 [0.1720, 0.3548] |
| S0-BG | fpr_0.001 | 3,953 | 0.5041 | 0.0011 | 0.1312 | 0.8172 [0.7312, 0.8925] | 0.1398 [0.0753, 0.2043] |
| S0-BG | fpr_0.0001 | 765 | 0.0472 | 0.0001 | 0.4122 | 0.6452 [0.5484, 0.7312] | 0.0323 [0.0000, 0.0753] |
| S0-B | fpr_0.001 | 4,473 | 0.6058 | 0.0014 | 0.1045 | 0.8172 [0.7419, 0.8925] | 0.1398 [0.0753, 0.2151] |
| S0-B | fpr_0.0001 | 697 | 0.0481 | 0.0002 | 0.3870 | 0.6882 [0.5914, 0.7745] | 0.0645 [0.0215, 0.1183] |
| iforest | fpr_0.001 | 2,259 | 0.3412 | 0.0008 | 0.0170 | 0.1183 [0.0538, 0.1828] | 0.0000 [0.0000, 0.0000] |
| iforest | fpr_0.0001 | 155 | 0.0244 | 0.0001 | 0.0000 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] |
| pca | fpr_0.001 | 3,856 | 0.5959 | 0.0013 | 0.0138 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] |
| pca | fpr_0.0001 | 473 | 0.0594 | 0.0002 | 0.0055 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] |
| activity | fpr_0.001 | 3,637 | 0.5507 | 0.0011 | 0.0153 | 0.0108 [0.0000, 0.0323] | 0.0000 [0.0000, 0.0000] |
| activity | fpr_0.0001 | 677 | 0.0802 | 0.0002 | 0.0000 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] |
| random | fpr_0.001 | 3,337 | 0.5467 | 0.0011 | 0.0009 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] |
| random | fpr_0.0001 | 332 | 0.0545 | 0.0001 | 0.0000 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] |

## Sensitivity: original label (incidental positives counted)

| Scorer | AUPRC | Precision | Detected | Linked |
| --- | --- | --- | --- | --- |
| S0-BG | 0.0743 [0.0667, 0.0828] | 0.1006 | 0.8387 [0.7527, 0.9140] | 0.1505 [0.0860, 0.2153] |
| oracle | 0.1142 [0.1034, 0.1260] | 0.1169 | 0.9140 [0.8495, 0.9677] | 0.6882 [0.5914, 0.7849] |

## Calibration (isotonic per member, two-fold cross-fitted on validation)

| Scorer | Brier (raw) | Brier (calibrated) | ECE (raw) | ECE (calibrated) | Prevalence |
| --- | --- | --- | --- | --- | --- |
| S0-BG | 0.0012 | 0.0012 | 0.0004 | 0.0000 | 0.0013 |
| oracle | 0.0012 | 0.0012 | 0.0003 | 0.0000 | 0.0013 |

## Most important features (share of total gain)

- **S0-BG:** `fmt_ach_share` 0.44, `amt_in` 0.09, `new_cp_share` 0.05, `cp_out_deg_max` 0.05, `fmt_credit_card_share` 0.03, `new_cp_n` 0.03, `amt_in_max` 0.03, `self_tx` 0.02, `amt_out` 0.02, `active_span_h` 0.02
- **oracle:** `fmt_ach_share` 0.37, `amt_net` 0.09, `cp_out_deg_max` 0.05, `new_cp_n` 0.04, `self_tx` 0.04, `new_cp_share` 0.04, `cp_in_deg_max` 0.03, `amt_vs_history` 0.03, `amt_in` 0.02, `active_span_h` 0.02

## Time per configuration

| Configuration | Train and score s | Evaluate s |
| --- | --- | --- |
| random | 5.70 | 35.30 |
| activity | 6.60 | 14.70 |
| S0-B | 16.90 | 16.50 |
| S0-BG | 26.00 | 15.10 |
| oracle | 84.60 | 27.80 |
| iforest | 79.00 | 17.10 |
| pca | 30.60 | 18.30 |
