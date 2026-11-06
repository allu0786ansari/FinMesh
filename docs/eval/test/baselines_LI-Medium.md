# Baselines · LI-Medium (seed 0)

> **Sealed test (week 18).** Every model trained on the training partition; every calibration, threshold, fusion and attribution parameter fitted on validation and frozen; test scored label-free, then opened once per seed through the logged seal (`finmesh sealed-log`). Wording below that says *validation* in a column or check name refers to the frozen rule; every number is on **test**.

Federation B8; test windows 39–50. Training windows 12–37 (burn-in before 12); windows 33–37 held out for early stopping and FPR thresholds. Label: primary (amendment A9: incidental positives masked). Primary operating point **alerts_1_per_1000_per_day** (A10); schemes count as detected within 12 windows of their first. S0 links alerts locally; the oracle links across members. Total 2,318 s, peak memory 2,464 MB.

## Validation at the primary budget (alerts_1_per_1000_per_day)

| Scorer | AUPRC [95% CI] | AUROC | Precision | Window recall | Detected [95% CI] | Random detected | Linked [95% CI] | Random linked | Linked across members | Median TTD h |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Oracle (pooled data, full graph) | 0.0777 [0.0679, 0.0886] | 0.9700 | 0.0988 | 0.1236 | 0.8830 [0.8085, 0.9468] | 0.0074 | 0.6064 [0.5000, 0.7021] | 0.0000 | 0.5851 | 0.0000 |
| S0 local GBDT, all features | 0.0542 [0.0467, 0.0625] | 0.9563 | 0.0827 | 0.1053 | 0.8085 [0.7234, 0.8830] | 0.0074 | 0.1064 [0.0532, 0.1702] | 0.0000 | 0.0000 | 0.0000 |
| S0 local GBDT, behaviour only | 0.0439 [0.0387, 0.0498] | 0.8957 | 0.0755 | 0.0976 | 0.7872 [0.6915, 0.8617] | 0.0074 | 0.1064 [0.0532, 0.1705] | 0.0000 | 0.0000 | 0.0000 |
| S0 alerts, linked across members (decomposition) | 0.0542 [0.0467, 0.0625] | 0.9563 | 0.0827 | 0.1053 | 0.8085 [0.7234, 0.8830] | 0.0074 | 0.5426 [0.4362, 0.6383] | 0.0000 | 0.5106 | 0.0000 |
| Oracle without format and self-transfer features (ablation) | 0.0286 [0.0250, 0.0330] | 0.9443 | 0.0747 | 0.0962 | 0.7128 [0.6170, 0.7979] | 0.0074 | 0.3617 [0.2660, 0.4574] | 0.0000 | 0.3511 | 0.0000 |
| S0 without format and self-transfer features (ablation) | 0.0218 [0.0190, 0.0259] | 0.9258 | 0.0638 | 0.0838 | 0.6383 [0.5423, 0.7234] | 0.0074 | 0.0426 [0.0106, 0.0851] | 0.0000 | 0.0000 | 0.0000 |
| Isolation Forest (local) | 0.0034 [0.0031, 0.0037] | 0.7634 | 0.0179 | 0.0239 | 0.1809 [0.0957, 0.2660] | 0.0074 | 0.0000 [0.0000, 0.0000] | 0.0000 | 0.0000 | 0.0000 |
| PCA reconstruction (local) | 0.0027 [0.0025, 0.0030] | 0.6467 | 0.0106 | 0.0142 | 0.0532 [0.0106, 0.0957] | 0.0074 | 0.0000 [0.0000, 0.0000] | 0.0000 | 0.0000 | 6.00 |
| Activity (legs in window) | 0.0011 [0.0010, 0.0012] | 0.4679 | 0.0090 | 0.0120 | 0.0106 [0.0000, 0.0319] | 0.0074 | 0.0000 [0.0000, 0.0000] | 0.0000 | 0.0000 | 0.0000 |
| Random | 0.0009 [0.0008, 0.0009] | 0.4953 | 0.0005 | 0.0007 | 0.0213 [0.0000, 0.0532] | 0.0074 | 0.0000 [0.0000, 0.0000] | 0.0000 | 0.0000 | 0.0000 |

Validation prevalence 0.0009; schemes evaluated 94.

## Gate G1 and PT4b comparisons (paired, same schemes and accounts)

| Difference | Linked detection | p (Holm) | Any-alert detection | p (Holm) | AUPRC | p |
| --- | --- | --- | --- | --- | --- | --- |
| oracle - S0-BG | 0.5000 [0.3936, 0.5957] | 0.0000 | 0.0745 [0.0213, 0.1383] | 0.0480 | 0.0235 [0.0182, 0.0288] | 0.0000 |
| S0-BG - S0-B | 0.0000 [-0.0532, 0.0532] | 1.00 | 0.0213 [-0.0426, 0.0957] | 1.00 | 0.0104 [0.0056, 0.0155] | 0.0000 |
| S0-BG - random | 0.1064 [0.0532, 0.1702] | 0.0000 | 0.7872 [0.6915, 0.8723] | 0.0000 | 0.0534 [0.0459, 0.0617] | 0.0000 |
| oracle-noart - S0-BG-noart | 0.3191 [0.2234, 0.4149] | 0.0000 | 0.0745 [0.0000, 0.1489] | 0.1620 | 0.0068 [0.0044, 0.0093] | 0.0000 |

## Secondary operating points (FPR budgets, thresholds from the held-out training windows)

| Scorer | Budget | Alerts | False alerts /1000 acc /day | Max member FPR | Precision | Detected | Linked |
| --- | --- | --- | --- | --- | --- | --- | --- |
| oracle | fpr_0.001 | 6,227 | 0.8359 | 0.0011 | 0.0957 | 0.8830 [0.8085, 0.9362] | 0.6383 [0.5319, 0.7340] |
| oracle | fpr_0.0001 | 1,555 | 0.1383 | 0.0002 | 0.2487 | 0.7766 [0.6915, 0.8617] | 0.4255 [0.3295, 0.5213] |
| S0-BG | fpr_0.001 | 5,521 | 0.7572 | 0.0012 | 0.0830 | 0.8298 [0.7447, 0.9043] | 0.1064 [0.0532, 0.1702] |
| S0-BG | fpr_0.0001 | 1,044 | 0.0874 | 0.0001 | 0.2719 | 0.6596 [0.5638, 0.7449] | 0.0638 [0.0213, 0.1170] |
| S0-B | fpr_0.001 | 4,926 | 0.6807 | 0.0010 | 0.0831 | 0.7872 [0.7021, 0.8617] | 0.1064 [0.0532, 0.1705] |
| S0-B | fpr_0.0001 | 1,032 | 0.0984 | 0.0002 | 0.2268 | 0.6170 [0.5106, 0.7128] | 0.0638 [0.0213, 0.1170] |
| oracle-noart | fpr_0.001 | 8,060 | 1.20 | 0.0015 | 0.0441 | 0.7447 [0.6489, 0.8298] | 0.3511 [0.2553, 0.4468] |
| oracle-noart | fpr_0.0001 | 1,720 | 0.2137 | 0.0003 | 0.1081 | 0.6170 [0.5213, 0.7128] | 0.1702 [0.0957, 0.2447] |
| S0-BG-noart | fpr_0.001 | 6,389 | 0.9519 | 0.0016 | 0.0448 | 0.6383 [0.5319, 0.7234] | 0.0426 [0.0106, 0.0851] |
| S0-BG-noart | fpr_0.0001 | 1,202 | 0.1571 | 0.0002 | 0.0885 | 0.4787 [0.3723, 0.5745] | 0.0000 [0.0000, 0.0000] |
| iforest | fpr_0.001 | 9,875 | 1.58 | 0.0022 | 0.0088 | 0.2766 [0.1809, 0.3723] | 0.0106 [0.0000, 0.0319] |
| iforest | fpr_0.0001 | 1,661 | 0.2598 | 0.0004 | 0.0063 | 0.0532 [0.0106, 0.0960] | 0.0000 [0.0000, 0.0000] |
| pca | fpr_0.001 | 5,113 | 0.8005 | 0.0011 | 0.0081 | 0.0426 [0.0106, 0.0851] | 0.0000 [0.0000, 0.0000] |
| pca | fpr_0.0001 | 541 | 0.0717 | 0.0001 | 0.0046 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] |
| activity | fpr_0.001 | 6,247 | 0.9785 | 0.0014 | 0.0077 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] |
| activity | fpr_0.0001 | 508 | 0.0525 | 0.0001 | 0.0000 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] |
| random | fpr_0.001 | 5,081 | 0.8330 | 0.0011 | 0.0002 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] |
| random | fpr_0.0001 | 476 | 0.0781 | 0.0001 | 0.0000 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] |

## Sensitivity: original label (incidental positives counted)

| Scorer | AUPRC | Precision | Detected | Linked |
| --- | --- | --- | --- | --- |
| S0-BG | 0.0525 [0.0450, 0.0609] | 0.0828 | 0.8085 [0.7234, 0.8830] | 0.1064 [0.0532, 0.1702] |
| oracle | 0.0742 [0.0647, 0.0839] | 0.0988 | 0.8830 [0.8085, 0.9468] | 0.6064 [0.5000, 0.7021] |

## Calibration (isotonic per member, two-fold cross-fitted on test)

| Scorer | Brier (raw) | Brier (calibrated) | ECE (raw) | ECE (calibrated) | Prevalence |
| --- | --- | --- | --- | --- | --- |
| S0-BG | 0.0009 | — | 0.0005 | — | 0.0009 |
| oracle | 0.0009 | — | 0.0006 | — | 0.0009 |

## Most important features (share of total gain)

- **S0-BG:** `fmt_ach_share` 0.44, `amt_in` 0.09, `new_cp_share` 0.05, `cp_out_deg_max` 0.05, `fmt_credit_card_share` 0.03, `new_cp_n` 0.03, `amt_in_max` 0.03, `self_tx` 0.02, `amt_out` 0.02, `active_span_h` 0.02
- **oracle:** `fmt_ach_share` 0.37, `amt_net` 0.09, `cp_out_deg_max` 0.05, `new_cp_n` 0.04, `self_tx` 0.04, `new_cp_share` 0.04, `cp_in_deg_max` 0.03, `amt_vs_history` 0.03, `amt_in` 0.02, `active_span_h` 0.02

## Time per configuration

| Configuration | Train and score s | Evaluate s |
| --- | --- | --- |
| random | 1.60 | 128.30 |
| activity | 0.9000 | 100.00 |
| S0-B | 11.60 | 103.50 |
| S0-BG | 14.90 | 99.80 |
| S0-BG-noart | 26.30 | 104.80 |
| oracle | 75.90 | 126.00 |
| oracle-noart | 35.10 | 108.80 |
| iforest | 71.40 | 107.00 |
| pca | 20.30 | 108.10 |
