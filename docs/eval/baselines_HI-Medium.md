# Baselines · HI-Medium (seed 0)

Federation B8; validation windows 39–50. Training windows 12–37 (burn-in before 12); windows 33–37 held out for early stopping and FPR thresholds. Label: primary (amendment A9: incidental positives masked). Primary operating point **alerts_1_per_1000_per_day** (A10); schemes count as detected within 12 windows of their first. S0 links alerts locally; the oracle links across members. Total 684 s, peak memory 1,722 MB.

## Validation at the primary budget (alerts_1_per_1000_per_day)

| Scorer | AUPRC [95% CI] | AUROC | Precision | Window recall | Detected [95% CI] | Random detected | Linked [95% CI] | Random linked | Linked across members | Median TTD h |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Oracle (pooled data, full graph) | 0.3929 [0.3762, 0.4071] | 0.9840 | 0.5734 | 0.2733 | 0.8857 [0.8584, 0.9129] | 0.0102 | 0.6824 [0.6425, 0.7205] | 0.0000 | 0.6352 | 0.0000 |
| S0 local GBDT, all features | 0.3361 [0.3192, 0.3508] | 0.9806 | 0.4915 | 0.2555 | 0.8639 [0.8330, 0.8911] | 0.0102 | 0.1742 [0.1434, 0.2051] | 0.0000 | 0.0000 | 0.0000 |
| S0 local GBDT, behaviour only | 0.2998 [0.2836, 0.3149] | 0.9551 | 0.4428 | 0.2474 | 0.8693 [0.8421, 0.8947] | 0.0102 | 0.1379 [0.1107, 0.1706] | 0.0000 | 0.0000 | 0.0000 |
| S0 alerts, linked across members (decomposition) | 0.3361 [0.3192, 0.3508] | 0.9806 | 0.4915 | 0.2555 | 0.8639 [0.8330, 0.8911] | 0.0102 | 0.6044 [0.5644, 0.6443] | 0.0000 | 0.5390 | 0.0000 |
| Oracle without format and self-transfer features (ablation) | 0.2612 [0.2466, 0.2742] | 0.9705 | 0.4483 | 0.2366 | 0.8621 [0.8330, 0.8911] | 0.0102 | 0.5880 [0.5463, 0.6298] | 0.0000 | 0.5318 | 0.0000 |
| S0 without format and self-transfer features (ablation) | 0.1953 [0.1821, 0.2087] | 0.9546 | 0.3620 | 0.2101 | 0.8367 [0.8040, 0.8675] | 0.0102 | 0.1325 [0.1053, 0.1615] | 0.0000 | 0.0000 | 0.0000 |
| Isolation Forest (local) | 0.0146 [0.0134, 0.0163] | 0.8246 | 0.0496 | 0.0439 | 0.2269 [0.1906, 0.2632] | 0.0102 | 0.0218 [0.0109, 0.0363] | 0.0000 | 0.0000 | 0.0000 |
| PCA reconstruction (local) | 0.0081 [0.0076, 0.0087] | 0.6841 | 0.0148 | 0.0136 | 0.0436 [0.0272, 0.0599] | 0.0102 | 0.0000 [0.0000, 0.0000] | 0.0000 | 0.0000 | 15.00 |
| Activity (legs in window) | 0.0025 [0.0024, 0.0027] | 0.4434 | 0.0173 | 0.0159 | 0.0163 [0.0054, 0.0290] | 0.0102 | 0.0000 [0.0000, 0.0000] | 0.0000 | 0.0000 | 12.00 |
| Random | 0.0019 [0.0019, 0.0020] | 0.5020 | 0.0021 | 0.0020 | 0.0073 [0.0018, 0.0146] | 0.0102 | 0.0000 [0.0000, 0.0000] | 0.0000 | 0.0000 | 0.0000 |

Validation prevalence 0.0019; schemes evaluated 551.

## Gate G1 and PT4b comparisons (paired, same schemes and accounts)

| Difference | Linked detection | p (Holm) | Any-alert detection | p (Holm) | AUPRC | p |
| --- | --- | --- | --- | --- | --- | --- |
| oracle - S0-BG | 0.5082 [0.4646, 0.5499] | 0.0000 | 0.0218 [-0.0018, 0.0454] | 0.1680 | 0.0568 [0.0511, 0.0623] | 0.0000 |
| S0-BG - S0-B | 0.0363 [0.0181, 0.0563] | 0.0000 | -0.0054 [-0.0345, 0.0218] | 0.7500 | 0.0363 [0.0295, 0.0442] | 0.0000 |
| S0-BG - random | 0.1742 [0.1434, 0.2051] | 0.0000 | 0.8566 [0.8258, 0.8838] | 0.0000 | 0.3341 [0.3173, 0.3488] | 0.0000 |
| oracle-noart - S0-BG-noart | 0.4555 [0.4138, 0.5009] | 0.0000 | 0.0254 [0.0018, 0.0508] | 0.1200 | 0.0659 [0.0578, 0.0743] | 0.0000 |

## Secondary operating points (FPR budgets, thresholds from the held-out training windows)

| Scorer | Budget | Alerts | False alerts /1000 acc /day | Max member FPR | Precision | Detected | Linked |
| --- | --- | --- | --- | --- | --- | --- | --- |
| oracle | fpr_0.001 | 8,012 | 0.3117 | 0.0006 | 0.5463 | 0.9474 [0.9274, 0.9655] | 0.8167 [0.7840, 0.8494] |
| oracle | fpr_0.0001 | 3,319 | 0.0141 | 0.0001 | 0.9262 | 0.7278 [0.6915, 0.7641] | 0.3394 [0.3012, 0.3775] |
| S0-BG | fpr_0.001 | 7,057 | 0.3030 | 0.0007 | 0.5113 | 0.9183 [0.8947, 0.9401] | 0.2087 [0.1742, 0.2414] |
| S0-BG | fpr_0.0001 | 3,110 | 0.0299 | 0.0001 | 0.8453 | 0.6715 [0.6298, 0.7114] | 0.0944 [0.0708, 0.1198] |
| S0-B | fpr_0.001 | 7,293 | 0.4003 | 0.0009 | 0.4267 | 0.9129 [0.8893, 0.9365] | 0.1688 [0.1379, 0.2015] |
| S0-B | fpr_0.0001 | 2,870 | 0.0369 | 0.0001 | 0.8079 | 0.7187 [0.6806, 0.7550] | 0.0526 [0.0345, 0.0726] |
| oracle-noart | fpr_0.001 | 5,089 | 0.1927 | 0.0004 | 0.5316 | 0.8203 [0.7877, 0.8530] | 0.4773 [0.4374, 0.5191] |
| oracle-noart | fpr_0.0001 | 2,370 | 0.0249 | 0.0001 | 0.8237 | 0.5844 [0.5444, 0.6279] | 0.1670 [0.1379, 0.1996] |
| S0-BG-noart | fpr_0.001 | 4,666 | 0.2431 | 0.0007 | 0.4237 | 0.7423 [0.7042, 0.7768] | 0.1125 [0.0853, 0.1397] |
| S0-BG-noart | fpr_0.0001 | 1,695 | 0.0258 | 0.0001 | 0.7601 | 0.4537 [0.4138, 0.4936] | 0.0200 [0.0091, 0.0327] |
| iforest | fpr_0.001 | 2,316 | 0.3157 | 0.0008 | 0.0589 | 0.1416 [0.1143, 0.1742] | 0.0054 [0.0000, 0.0127] |
| iforest | fpr_0.0001 | 163 | 0.0202 | 0.0001 | 0.1429 | 0.0345 [0.0218, 0.0508] | 0.0036 [0.0000, 0.0091] |
| pca | fpr_0.001 | 4,051 | 0.6097 | 0.0013 | 0.0143 | 0.0218 [0.0109, 0.0345] | 0.0000 [0.0000, 0.0000] |
| pca | fpr_0.0001 | 577 | 0.0713 | 0.0002 | 0.0000 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] |
| activity | fpr_0.001 | 3,668 | 0.5415 | 0.0011 | 0.0195 | 0.0109 [0.0036, 0.0200] | 0.0000 [0.0000, 0.0000] |
| activity | fpr_0.0001 | 677 | 0.0788 | 0.0002 | 0.0000 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] |
| random | fpr_0.001 | 3,391 | 0.5423 | 0.0011 | 0.0021 | 0.0054 [0.0000, 0.0127] | 0.0000 [0.0000, 0.0000] |
| random | fpr_0.0001 | 327 | 0.0523 | 0.0001 | 0.0000 | 0.0000 [0.0000, 0.0000] | 0.0000 [0.0000, 0.0000] |

## Sensitivity: original label (incidental positives counted)

| Scorer | AUPRC | Precision | Detected | Linked |
| --- | --- | --- | --- | --- |
| S0-BG | 0.3264 [0.3129, 0.3410] | 0.4915 | 0.8639 [0.8330, 0.8911] | 0.1742 [0.1434, 0.2051] |
| oracle | 0.3810 [0.3684, 0.3952] | 0.5734 | 0.8857 [0.8584, 0.9129] | 0.6824 [0.6425, 0.7205] |

## Calibration (isotonic per member, two-fold cross-fitted on validation)

| Scorer | Brier (raw) | Brier (calibrated) | ECE (raw) | ECE (calibrated) | Prevalence |
| --- | --- | --- | --- | --- | --- |
| S0-BG | 0.0017 | 0.0015 | 0.0011 | 0.0000 | 0.0019 |
| oracle | 0.0015 | 0.0014 | 0.0007 | 0.0000 | 0.0019 |

## Most important features (share of total gain)

- **S0-BG:** `fmt_ach_share` 0.23, `amt_in_max` 0.15, `self_tx` 0.13, `new_cp_n` 0.07, `new_cp_share` 0.03, `amt_in` 0.03, `amt_out` 0.03, `cp_out_deg_max` 0.02, `amt_net` 0.02, `amt_vs_history` 0.02
- **oracle:** `self_tx` 0.25, `amt_in_max` 0.19, `fmt_ach_share` 0.16, `new_cp_share` 0.09, `amt_net` 0.03, `cp_out_deg_max` 0.02, `new_cp_n` 0.02, `amt_in` 0.02, `cross_currency_share` 0.02, `active_span_h` 0.01

## Time per configuration

| Configuration | Train and score s | Evaluate s |
| --- | --- | --- |
| random | 3.40 | 30.80 |
| activity | 2.60 | 16.00 |
| S0-B | 20.60 | 14.70 |
| S0-BG | 36.80 | 16.30 |
| S0-BG-noart | 34.10 | 15.80 |
| oracle | 129.60 | 27.30 |
| oracle-noart | 72.20 | 16.10 |
| iforest | 50.10 | 14.80 |
| pca | 15.50 | 15.70 |
