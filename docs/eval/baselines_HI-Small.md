# Baselines · HI-Small (seed 0)

Federation B8; validation windows 23–30. Training windows 12–21 (burn-in before 12); windows 20–21 held out for early stopping and FPR thresholds. Label: primary (amendment A9: incidental positives masked). Primary operating point **alerts_1_per_1000_per_day** (A10); schemes count as detected within 12 windows of their first. S0 links alerts locally; the oracle links across members. Total 59 s, peak memory 700 MB.

## Validation at the primary budget (alerts_1_per_1000_per_day)

| Scorer | AUPRC [95% CI] | AUROC | Precision | Window recall | Detected [95% CI] | Random detected | Linked [95% CI] | Random linked | Linked across members | Median TTD h |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Oracle (pooled data, full graph) | 0.3254 [0.2954, 0.3571] | 0.9791 | 0.4709 | 0.2544 | 0.8971 [0.8235, 0.9562] | 0.0105 | 0.6176 [0.5143, 0.7353] | 0.0000 | 0.5735 | 0.0000 |
| S0 local GBDT, all features | 0.1720 [0.1451, 0.1990] | 0.9373 | 0.3068 | 0.1961 | 0.8235 [0.7353, 0.9118] | 0.0105 | 0.1471 [0.0588, 0.2353] | 0.0000 | 0.0000 | 0.0000 |
| S0 local GBDT, behaviour only | 0.1648 [0.1424, 0.1887] | 0.9164 | 0.2787 | 0.1841 | 0.8382 [0.7647, 0.9265] | 0.0105 | 0.1176 [0.0441, 0.2059] | 0.0000 | 0.0000 | 0.0000 |
| Isolation Forest (local) | 0.0144 [0.0101, 0.0221] | 0.8456 | 0.0460 | 0.0407 | 0.2941 [0.1912, 0.3971] | 0.0105 | 0.0000 [0.0000, 0.0000] | 0.0000 | 0.0000 | 12.00 |
| PCA reconstruction (local) | 0.0049 [0.0041, 0.0063] | 0.7009 | 0.0173 | 0.0157 | 0.1176 [0.0441, 0.2059] | 0.0105 | 0.0000 [0.0000, 0.0000] | 0.0000 | 0.0000 | 6.00 |
| Activity (legs in window) | 0.0020 [0.0017, 0.0024] | 0.4662 | 0.0158 | 0.0139 | 0.0294 [0.0000, 0.0735] | 0.0105 | 0.0000 [0.0000, 0.0000] | 0.0000 | 0.0000 | 6.00 |
| Random | 0.0016 [0.0015, 0.0018] | 0.5094 | 0.0029 | 0.0028 | 0.0441 [0.0000, 0.1029] | 0.0105 | 0.0000 [0.0000, 0.0000] | 0.0000 | 0.0000 | 6.00 |

Validation prevalence 0.0015; schemes evaluated 68.

## Gate G1 and PT4b comparisons (paired, same schemes and accounts)

| Difference | Linked detection | p (Holm) | Any-alert detection | p (Holm) | AUPRC | p |
| --- | --- | --- | --- | --- | --- | --- |
| oracle - S0-BG | 0.4706 [0.3673, 0.5882] | 0.0000 | 0.0735 [-0.0004, 0.1618] | 0.3420 | 0.1534 [0.1294, 0.1736] | 0.0000 |
| S0-BG - S0-B | 0.0294 [0.0000, 0.0735] | 0.5160 | -0.0147 [-0.0588, 0.0294] | 0.7760 | 0.0072 [-0.0071, 0.0207] | 0.3200 |
| S0-BG - random | 0.1471 [0.0588, 0.2353] | 0.0000 | 0.7794 [0.6765, 0.8824] | 0.0000 | 0.1704 [0.1435, 0.1973] | 0.0000 |

## Secondary operating points (FPR budgets, thresholds from the held-out training windows)

| Scorer | Budget | Alerts | False alerts /1000 acc /day | Max member FPR | Precision | Detected | Linked |
| --- | --- | --- | --- | --- | --- | --- | --- |
| oracle | fpr_0.001 | 1,682 | 0.7581 | 0.0015 | 0.3250 | 0.9853 [0.9559, 1.00] | 0.7941 [0.6912, 0.8827] |
| oracle | fpr_0.0001 | 674 | 0.0709 | 0.0003 | 0.7411 | 0.8382 [0.7500, 0.9265] | 0.5735 [0.4559, 0.6768] |
| S0-BG | fpr_0.001 | 1,347 | 0.6805 | 0.0012 | 0.2683 | 0.8824 [0.8088, 0.9559] | 0.1618 [0.0735, 0.2504] |
| S0-BG | fpr_0.0001 | 352 | 0.0612 | 0.0002 | 0.6400 | 0.6618 [0.5585, 0.7647] | 0.1029 [0.0441, 0.1765] |
| S0-B | fpr_0.001 | 1,261 | 0.6581 | 0.0014 | 0.2606 | 0.8824 [0.8088, 0.9559] | 0.1176 [0.0441, 0.2059] |
| S0-B | fpr_0.0001 | 335 | 0.0631 | 0.0002 | 0.6286 | 0.7206 [0.6176, 0.8235] | 0.0882 [0.0294, 0.1618] |
| iforest | fpr_0.001 | 864 | 0.7397 | 0.0014 | 0.0463 | 0.2647 [0.1765, 0.3680] | 0.0000 [0.0000, 0.0000] |
| iforest | fpr_0.0001 | 114 | 0.0961 | 0.0003 | 0.0748 | 0.0588 [0.0147, 0.1176] | 0.0000 [0.0000, 0.0000] |
| pca | fpr_0.001 | 838 | 0.7649 | 0.0017 | 0.0187 | 0.1176 [0.0441, 0.2059] | 0.0000 [0.0000, 0.0000] |
| pca | fpr_0.0001 | 109 | 0.1048 | 0.0003 | 0.0092 | 0.0147 [0.0000, 0.0441] | 0.0000 [0.0000, 0.0000] |
| activity | fpr_0.001 | 847 | 0.7426 | 0.0016 | 0.0129 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] |
| activity | fpr_0.0001 | 154 | 0.1223 | 0.0004 | 0.0000 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] |
| random | fpr_0.001 | 728 | 0.7038 | 0.0014 | 0.0028 | 0.0294 [0.0000, 0.0735] | 0.0000 [0.0000, 0.0000] |
| random | fpr_0.0001 | 110 | 0.1068 | 0.0004 | 0.0000 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] |

## Sensitivity: original label (incidental positives counted)

| Scorer | AUPRC | Precision | Detected | Linked |
| --- | --- | --- | --- | --- |
| S0-BG | 0.1627 [0.1345, 0.1901] | 0.3068 | 0.8235 [0.7353, 0.9118] | 0.1471 [0.0588, 0.2353] |
| oracle | 0.3070 [0.2700, 0.3422] | 0.4709 | 0.8971 [0.8235, 0.9562] | 0.6176 [0.5143, 0.7353] |

## Calibration (isotonic per member, two-fold cross-fitted on validation)

| Scorer | Brier (raw) | Brier (calibrated) | ECE (raw) | ECE (calibrated) | Prevalence |
| --- | --- | --- | --- | --- | --- |
| S0-BG | 0.0016 | 0.0014 | 0.0011 | 0.0001 | 0.0015 |
| oracle | 0.0012 | 0.0012 | 0.0004 | 0.0001 | 0.0015 |

## Most important features (share of total gain)

- **S0-BG:** `fmt_ach_share` 0.39, `amt_in_max` 0.05, `amt_vs_history` 0.04, `legs_vs_history` 0.03, `amt_net` 0.03, `amt_out_max` 0.03, `active_span_h` 0.03, `cp_in_deg_max` 0.03, `amt_in` 0.03, `in_amount_hhi` 0.03
- **oracle:** `fmt_ach_share` 0.33, `amt_in_max` 0.12, `amt_out` 0.09, `cp_out_deg_max` 0.03, `amt_in` 0.03, `fmt_cheque_share` 0.03, `cp_in_deg_max` 0.03, `new_cp_n` 0.03, `self_tx` 0.03, `amt_vs_history` 0.02

## Time per configuration

| Configuration | Train and score s | Evaluate s |
| --- | --- | --- |
| random | 0.4000 | 4.60 |
| activity | 0.3000 | 2.30 |
| S0-B | 2.50 | 2.40 |
| S0-BG | 3.30 | 2.60 |
| oracle | 2.40 | 4.40 |
| iforest | 9.70 | 2.60 |
| pca | 2.70 | 2.30 |
