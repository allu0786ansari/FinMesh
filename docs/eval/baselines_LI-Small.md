# Baselines · LI-Small (seed 0)

Federation B8; validation windows 23–30. Training windows 12–21 (burn-in before 12); windows 20–21 held out for early stopping and FPR thresholds. Label: primary (amendment A9: incidental positives masked). Primary operating point **alerts_1_per_1000_per_day** (A10); schemes count as detected within 12 windows of their first. S0 links alerts locally; the oracle links across members. Total 77 s, peak memory 755 MB.

## Validation at the primary budget (alerts_1_per_1000_per_day)

| Scorer | AUPRC [95% CI] | AUROC | Precision | Window recall | Detected [95% CI] | Random detected | Linked [95% CI] | Random linked | Linked across members | Median TTD h |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Oracle (pooled data, full graph) | 0.0783 [0.0655, 0.0940] | 0.9725 | 0.0916 | 0.1123 | 0.7391 [0.5652, 0.9130] | 0.0085 | 0.3913 [0.2174, 0.5652] | 0.0000 | 0.3913 | 0.0000 |
| S0 local GBDT, all features | 0.0370 [0.0319, 0.0454] | 0.9477 | 0.0643 | 0.0845 | 0.6087 [0.3913, 0.7826] | 0.0085 | 0.0000 [0.0000, 0.0000] | 0.0000 | 0.0000 | 0.0000 |
| S0 local GBDT, behaviour only | 0.0274 [0.0238, 0.0337] | 0.8810 | 0.0520 | 0.0696 | 0.7391 [0.5652, 0.9130] | 0.0085 | 0.0000 [0.0000, 0.0000] | 0.0000 | 0.0000 | 0.0000 |
| Isolation Forest (local) | 0.0069 [0.0051, 0.0105] | 0.8111 | 0.0207 | 0.0278 | 0.3043 [0.1304, 0.4783] | 0.0085 | 0.0000 [0.0000, 0.0000] | 0.0000 | 0.0000 | 18.00 |
| PCA reconstruction (local) | 0.0019 [0.0017, 0.0022] | 0.6628 | 0.0000 | 0.0000 | 0.0000 [0.0000, 0.0000] | 0.0085 | 0.0000 [0.0000, 0.0000] | 0.0000 | 0.0000 | — |
| Activity (legs in window) | 0.0016 [0.0013, 0.0021] | 0.4246 | 0.0152 | 0.0199 | 0.0870 [0.0000, 0.2174] | 0.0085 | 0.0000 [0.0000, 0.0000] | 0.0000 | 0.0000 | 12.00 |
| Random | 0.0011 [0.0010, 0.0012] | 0.5073 | 0.0007 | 0.0010 | 0.0435 [0.0000, 0.1304] | 0.0085 | 0.0000 [0.0000, 0.0000] | 0.0000 | 0.0000 | 24.00 |

Validation prevalence 0.0010; schemes evaluated 23.

## Gate G1 and PT4b comparisons (paired, same schemes and accounts)

| Difference | Linked detection | p (Holm) | Any-alert detection | p (Holm) | AUPRC | p |
| --- | --- | --- | --- | --- | --- | --- |
| oracle - S0-BG | 0.3913 [0.2174, 0.5652] | 0.0000 | 0.1304 [-0.0435, 0.3043] | 0.6360 | 0.0414 [0.0301, 0.0529] | 0.0000 |
| S0-BG - S0-B | 0.0000 [0.0000, 0.0000] | 1.00 | -0.1304 [-0.2609, 0.0000] | 0.3360 | 0.0095 [0.0061, 0.0138] | 0.0000 |
| S0-BG - random | 0.0000 [0.0000, 0.0000] | 1.00 | 0.5652 [0.3478, 0.7391] | 0.0000 | 0.0359 [0.0308, 0.0443] | 0.0000 |

## Secondary operating points (FPR budgets, thresholds from the held-out training windows)

| Scorer | Budget | Alerts | False alerts /1000 acc /day | Max member FPR | Precision | Detected | Linked |
| --- | --- | --- | --- | --- | --- | --- | --- |
| oracle | fpr_0.001 | 1,279 | 0.7111 | 0.0013 | 0.0963 | 0.7391 [0.5652, 0.9130] | 0.3913 [0.2174, 0.5652] |
| oracle | fpr_0.0001 | 299 | 0.0914 | 0.0002 | 0.2629 | 0.6522 [0.4348, 0.8261] | 0.2174 [0.0870, 0.3913] |
| S0-BG | fpr_0.001 | 1,179 | 0.7352 | 0.0012 | 0.0589 | 0.5652 [0.3478, 0.7391] | 0.0000 [0.0000, 0.0000] |
| S0-BG | fpr_0.0001 | 184 | 0.0949 | 0.0002 | 0.1007 | 0.3913 [0.2174, 0.6087] | 0.0000 [0.0000, 0.0000] |
| S0-B | fpr_0.001 | 1,351 | 0.8691 | 0.0017 | 0.0510 | 0.7826 [0.6087, 0.9565] | 0.0000 [0.0000, 0.0000] |
| S0-B | fpr_0.0001 | 185 | 0.1091 | 0.0003 | 0.0941 | 0.3043 [0.1304, 0.4783] | 0.0000 [0.0000, 0.0000] |
| iforest | fpr_0.001 | 1,132 | 0.7551 | 0.0013 | 0.0211 | 0.2609 [0.0870, 0.4348] | 0.0000 [0.0000, 0.0000] |
| iforest | fpr_0.0001 | 182 | 0.1197 | 0.0003 | 0.0287 | 0.1739 [0.0435, 0.3478] | 0.0000 [0.0000, 0.0000] |
| pca | fpr_0.001 | 1,004 | 0.6963 | 0.0012 | 0.0000 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] |
| pca | fpr_0.0001 | 129 | 0.0914 | 0.0002 | 0.0000 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] |
| activity | fpr_0.001 | 1,298 | 0.8429 | 0.0016 | 0.0165 | 0.0870 [0.0000, 0.2174] | 0.0000 [0.0000, 0.0000] |
| activity | fpr_0.0001 | 207 | 0.1204 | 0.0003 | 0.0000 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] |
| random | fpr_0.001 | 972 | 0.6871 | 0.0012 | 0.0010 | 0.0435 [0.0000, 0.1304] | 0.0000 [0.0000, 0.0000] |
| random | fpr_0.0001 | 89 | 0.0630 | 0.0001 | 0.0000 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] |

## Sensitivity: original label (incidental positives counted)

| Scorer | AUPRC | Precision | Detected | Linked |
| --- | --- | --- | --- | --- |
| S0-BG | 0.0365 [0.0309, 0.0437] | 0.0665 | 0.6087 [0.3913, 0.7826] | 0.0000 [0.0000, 0.0000] |
| oracle | 0.0736 [0.0597, 0.0895] | 0.0916 | 0.7391 [0.5652, 0.9130] | 0.3913 [0.2174, 0.5652] |

## Calibration (isotonic per member, two-fold cross-fitted on validation)

| Scorer | Brier (raw) | Brier (calibrated) | ECE (raw) | ECE (calibrated) | Prevalence |
| --- | --- | --- | --- | --- | --- |
| S0-BG | 0.0011 | 0.0010 | 0.0006 | 0.0001 | 0.0010 |
| oracle | 0.0010 | 0.0010 | 0.0004 | 0.0001 | 0.0010 |

## Most important features (share of total gain)

- **S0-BG:** `fmt_ach_share` 0.34, `amt_vs_history` 0.06, `cp_out_deg_max` 0.04, `active_span_h` 0.04, `amt_net` 0.04, `amt_in_max` 0.04, `legs_vs_history` 0.03, `amt_in` 0.03, `prior_leg_rate` 0.03, `new_cp_share` 0.03
- **oracle:** `fmt_ach_share` 0.36, `amt_in_max` 0.09, `cp_out_deg_max` 0.05, `self_tx` 0.05, `new_cp_share` 0.04, `new_cp_n` 0.04, `cp_in_deg_max` 0.03, `fmt_cheque_share` 0.03, `active_span_h` 0.03, `fmt_credit_card_share` 0.03

## Time per configuration

| Configuration | Train and score s | Evaluate s |
| --- | --- | --- |
| random | 0.7000 | 6.20 |
| activity | 0.4000 | 3.00 |
| S0-B | 2.50 | 3.30 |
| S0-BG | 3.40 | 3.10 |
| oracle | 2.90 | 6.20 |
| iforest | 12.50 | 3.20 |
| pca | 3.50 | 3.20 |
