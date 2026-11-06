# Baselines · HI-Medium (seed 0)

> **Sealed test (week 18).** Every model trained on the training partition; every calibration, threshold, fusion and attribution parameter fitted on validation and frozen; test scored label-free, then opened once per seed through the logged seal (`finmesh sealed-log`). Wording below that says *validation* in a column or check name refers to the frozen rule; every number is on **test**.

Federation B8; test windows 39–50. Training windows 12–37 (burn-in before 12); windows 33–37 held out for early stopping and FPR thresholds. Label: primary (amendment A9: incidental positives masked). Primary operating point **alerts_1_per_1000_per_day** (A10); schemes count as detected within 12 windows of their first. S0 links alerts locally; the oracle links across members. Total 2,757 s, peak memory 2,486 MB.

## Validation at the primary budget (alerts_1_per_1000_per_day)

| Scorer | AUPRC [95% CI] | AUROC | Precision | Window recall | Detected [95% CI] | Random detected | Linked [95% CI] | Random linked | Linked across members | Median TTD h |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Oracle (pooled data, full graph) | 0.2507 [0.2376, 0.2658] | 0.9753 | 0.4664 | 0.2057 | 0.8600 [0.8300, 0.8880] | 0.0063 | 0.6040 [0.5600, 0.6480] | 0.0000 | 0.5600 | 0.0000 |
| S0 local GBDT, all features | 0.2014 [0.1888, 0.2145] | 0.9688 | 0.3840 | 0.1882 | 0.8160 [0.7820, 0.8500] | 0.0063 | 0.1460 [0.1160, 0.1740] | 0.0000 | 0.0000 | 0.0000 |
| S0 local GBDT, behaviour only | 0.1864 [0.1749, 0.1984] | 0.9322 | 0.3392 | 0.1812 | 0.8220 [0.7880, 0.8540] | 0.0063 | 0.1180 [0.0900, 0.1460] | 0.0000 | 0.0000 | 0.0000 |
| S0 alerts, linked across members (decomposition) | 0.2014 [0.1888, 0.2145] | 0.9688 | 0.3840 | 0.1882 | 0.8160 [0.7820, 0.8500] | 0.0063 | 0.5380 [0.4960, 0.5800] | 0.0000 | 0.4700 | 0.0000 |
| Oracle without format and self-transfer features (ablation) | 0.1234 [0.1138, 0.1339] | 0.9522 | 0.3467 | 0.1684 | 0.7880 [0.7540, 0.8220] | 0.0063 | 0.4560 [0.4140, 0.5020] | 0.0000 | 0.4220 | 0.0000 |
| S0 without format and self-transfer features (ablation) | 0.0819 [0.0749, 0.0896] | 0.9296 | 0.2715 | 0.1471 | 0.7480 [0.7120, 0.7840] | 0.0063 | 0.0840 [0.0600, 0.1080] | 0.0000 | 0.0000 | 0.0000 |
| Isolation Forest (local) | 0.0065 [0.0060, 0.0070] | 0.7925 | 0.0248 | 0.0210 | 0.1440 [0.1140, 0.1780] | 0.0063 | 0.0140 [0.0040, 0.0240] | 0.0000 | 0.0000 | 0.0000 |
| PCA reconstruction (local) | 0.0048 [0.0045, 0.0051] | 0.6946 | 0.0108 | 0.0095 | 0.0140 [0.0040, 0.0240] | 0.0063 | 0.0000 [0.0000, 0.0000] | 0.0000 | 0.0000 | 0.0000 |
| Activity (legs in window) | 0.0017 [0.0016, 0.0018] | 0.4795 | 0.0124 | 0.0108 | 0.0100 [0.0020, 0.0200] | 0.0063 | 0.0000 [0.0000, 0.0000] | 0.0000 | 0.0000 | 6.00 |
| Random | 0.0013 [0.0013, 0.0014] | 0.4994 | 0.0014 | 0.0013 | 0.0080 [0.0020, 0.0160] | 0.0063 | 0.0000 [0.0000, 0.0000] | 0.0000 | 0.0000 | 6.00 |

Validation prevalence 0.0013; schemes evaluated 500.

## Gate G1 and PT4b comparisons (paired, same schemes and accounts)

| Difference | Linked detection | p (Holm) | Any-alert detection | p (Holm) | AUPRC | p |
| --- | --- | --- | --- | --- | --- | --- |
| oracle - S0-BG | 0.4580 [0.4100, 0.5080] | 0.0000 | 0.0440 [0.0180, 0.0700] | 0.0000 | 0.0494 [0.0431, 0.0560] | 0.0000 |
| S0-BG - S0-B | 0.0280 [0.0080, 0.0460] | 0.0300 | -0.0060 [-0.0340, 0.0240] | 0.6800 | 0.0149 [0.0085, 0.0213] | 0.0000 |
| S0-BG - random | 0.1460 [0.1160, 0.1740] | 0.0000 | 0.8080 [0.7740, 0.8420] | 0.0000 | 0.2000 [0.1875, 0.2131] | 0.0000 |
| oracle-noart - S0-BG-noart | 0.3720 [0.3320, 0.4160] | 0.0000 | 0.0400 [0.0060, 0.0740] | 0.0440 | 0.0415 [0.0349, 0.0482] | 0.0000 |

## Secondary operating points (FPR budgets, thresholds from the held-out training windows)

| Scorer | Budget | Alerts | False alerts /1000 acc /day | Max member FPR | Precision | Detected | Linked |
| --- | --- | --- | --- | --- | --- | --- | --- |
| oracle | fpr_0.001 | 13,533 | 1.13 | 0.0015 | 0.2431 | 0.9500 [0.9280, 0.9680] | 0.8480 [0.8180, 0.8800] |
| oracle | fpr_0.0001 | 5,497 | 0.1631 | 0.0003 | 0.5708 | 0.8060 [0.7720, 0.8380] | 0.5580 [0.5160, 0.6000] |
| S0-BG | fpr_0.001 | 12,936 | 1.17 | 0.0015 | 0.2110 | 0.9280 [0.9040, 0.9480] | 0.2200 [0.1840, 0.2540] |
| S0-BG | fpr_0.0001 | 4,102 | 0.1263 | 0.0003 | 0.5526 | 0.6960 [0.6600, 0.7360] | 0.1140 [0.0880, 0.1400] |
| S0-B | fpr_0.001 | 11,059 | 0.9682 | 0.0013 | 0.2244 | 0.8980 [0.8720, 0.9240] | 0.1700 [0.1380, 0.2020] |
| S0-B | fpr_0.0001 | 3,615 | 0.1274 | 0.0002 | 0.5277 | 0.7080 [0.6700, 0.7480] | 0.0740 [0.0520, 0.0960] |
| oracle-noart | fpr_0.001 | 16,704 | 1.88 | 0.0024 | 0.1186 | 0.8860 [0.8580, 0.9120] | 0.6560 [0.6160, 0.6980] |
| oracle-noart | fpr_0.0001 | 4,164 | 0.2049 | 0.0003 | 0.3869 | 0.6740 [0.6340, 0.7140] | 0.2860 [0.2460, 0.3240] |
| S0-BG-noart | fpr_0.001 | 13,602 | 1.55 | 0.0022 | 0.1133 | 0.8100 [0.7760, 0.8420] | 0.1380 [0.1080, 0.1660] |
| S0-BG-noart | fpr_0.0001 | 3,080 | 0.1695 | 0.0003 | 0.3490 | 0.5780 [0.5380, 0.6200] | 0.0420 [0.0260, 0.0600] |
| iforest | fpr_0.001 | 11,301 | 1.71 | 0.0025 | 0.0188 | 0.2200 [0.1840, 0.2560] | 0.0160 [0.0060, 0.0280] |
| iforest | fpr_0.0001 | 1,976 | 0.2881 | 0.0004 | 0.0191 | 0.0620 [0.0420, 0.0820] | 0.0080 [0.0000, 0.0160] |
| pca | fpr_0.001 | 5,344 | 0.8159 | 0.0011 | 0.0101 | 0.0140 [0.0060, 0.0260] | 0.0000 [0.0000, 0.0000] |
| pca | fpr_0.0001 | 636 | 0.0794 | 0.0001 | 0.0000 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] |
| activity | fpr_0.001 | 6,404 | 0.9714 | 0.0013 | 0.0109 | 0.0140 [0.0040, 0.0260] | 0.0000 [0.0000, 0.0000] |
| activity | fpr_0.0001 | 550 | 0.0560 | 0.0001 | 0.0000 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] |
| random | fpr_0.001 | 5,192 | 0.8313 | 0.0011 | 0.0012 | 0.0060 [0.0000, 0.0140] | 0.0000 [0.0000, 0.0000] |
| random | fpr_0.0001 | 460 | 0.0737 | 0.0001 | 0.0022 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] |

## Sensitivity: original label (incidental positives counted)

| Scorer | AUPRC | Precision | Detected | Linked |
| --- | --- | --- | --- | --- |
| S0-BG | 0.1952 [0.1827, 0.2073] | 0.3840 | 0.8160 [0.7820, 0.8500] | 0.1460 [0.1160, 0.1740] |
| oracle | 0.2427 [0.2288, 0.2560] | 0.4664 | 0.8600 [0.8300, 0.8880] | 0.6040 [0.5600, 0.6480] |

## Calibration (isotonic per member, two-fold cross-fitted on test)

| Scorer | Brier (raw) | Brier (calibrated) | ECE (raw) | ECE (calibrated) | Prevalence |
| --- | --- | --- | --- | --- | --- |
| S0-BG | 0.0017 | — | 0.0020 | — | 0.0013 |
| oracle | 0.0014 | — | 0.0014 | — | 0.0013 |

## Most important features (share of total gain)

- **S0-BG:** `fmt_ach_share` 0.23, `amt_in_max` 0.15, `self_tx` 0.13, `new_cp_n` 0.07, `new_cp_share` 0.03, `amt_in` 0.03, `amt_out` 0.03, `cp_out_deg_max` 0.02, `amt_net` 0.02, `amt_vs_history` 0.02
- **oracle:** `self_tx` 0.25, `amt_in_max` 0.19, `fmt_ach_share` 0.16, `new_cp_share` 0.09, `amt_net` 0.03, `cp_out_deg_max` 0.02, `new_cp_n` 0.02, `amt_in` 0.02, `cross_currency_share` 0.02, `active_span_h` 0.01

## Time per configuration

| Configuration | Train and score s | Evaluate s |
| --- | --- | --- |
| random | 1.80 | 146.00 |
| activity | 0.9000 | 107.90 |
| S0-B | 25.90 | 116.50 |
| S0-BG | 40.90 | 115.50 |
| S0-BG-noart | 38.00 | 114.10 |
| oracle | 153.90 | 136.40 |
| oracle-noart | 86.40 | 120.90 |
| iforest | 72.50 | 117.00 |
| pca | 20.00 | 117.90 |
