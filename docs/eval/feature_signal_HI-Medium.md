# Single-feature signal · HI-Medium

Federation B8, feature schema v2, val partition: 3,388,224 account-windows, 6,764 positive (prevalence 0.0020). Each feature alone ranks the account-windows; AUPRC uses the better direction, chosen on these same rows, so the table is descriptive. Lift = AUPRC / prevalence.

**Leakage check:** no feature reaches AUROC 0.95 or AUPRC 0.5 on its own.

| Feature | Family | Present | Mean (positive) | Mean (negative) | AUROC | Better | AUPRC | Lift |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fmt_ach_share | behaviour | 1.00 | 0.7765 | 0.1131 | 0.8906 | high | 0.0250 | 12.53 |
| fan_out | graph | 1.00 | 31.51 | 0.5853 | 0.5286 | high | 0.0212 | 10.61 |
| nb_out_deg | neighbourhood | 1.00 | 95.53 | 1.06 | 0.5106 | high | 0.0208 | 10.42 |
| new_cp_n | graph | 1.00 | 4.86 | 0.2500 | 0.8029 | high | 0.0206 | 10.30 |
| amt_vs_history | history | 1.00 | 3.55 | 0.5957 | 0.7105 | high | 0.0097 | 4.88 |
| fan_in | graph | 1.00 | 1.67 | 0.6452 | 0.5507 | high | 0.0093 | 4.67 |
| nb_in_deg | neighbourhood | 1.00 | 1.99 | 0.9307 | 0.5564 | high | 0.0086 | 4.29 |
| cyc2 | neighbourhood | 1.00 | 0.0483 | 0.0006 | 0.5228 | high | 0.0084 | 4.19 |
| fmt_cheque_share | behaviour | 1.00 | 0.1095 | 0.4367 | 0.1674 | low | 0.0078 | 3.89 |
| legs_vs_history | history | 1.00 | 0.7584 | 0.6027 | 0.5601 | high | 0.0077 | 3.84 |
| amt_out | behaviour | 1.00 | 12,093,975.03 | 223,503.17 | 0.5627 | high | 0.0074 | 3.71 |
| sg_out_max | neighbourhood | 1.00 | 0.1359 | 0.0935 | 0.5169 | high | 0.0064 | 3.23 |
| new_cp_share | graph | 0.9987 | 0.7094 | 0.1912 | 0.7889 | high | 0.0062 | 3.11 |
| prior_leg_rate | history | 1.00 | 58.05 | 0.8930 | 0.3523 | low | 0.0056 | 2.80 |
| currencies_n | behaviour | 1.00 | 1.13 | 1.01 | 0.5579 | high | 0.0055 | 2.78 |
| prior_active_windows | history | 1.00 | 2.94 | 3.96 | 0.3564 | low | 0.0051 | 2.55 |
| recency_windows | history | 1.00 | 5.88 | 3.73 | 0.5982 | high | 0.0050 | 2.49 |
| cross_currency_share | behaviour | 1.00 | 0.0710 | 0.0060 | 0.5578 | high | 0.0048 | 2.40 |
| amt_out_max | behaviour | 1.00 | 3,879,945.99 | 177,630.78 | 0.5710 | high | 0.0045 | 2.23 |
| fmt_credit_card_share | behaviour | 1.00 | 0.0671 | 0.3190 | 0.2414 | low | 0.0043 | 2.17 |
| cyc3 | neighbourhood | 1.00 | 0.0041 | 0.0000 | 0.5019 | high | 0.0043 | 2.15 |
| self_tx | behaviour | 1.00 | 0.1391 | 0.0248 | 0.5570 | high | 0.0042 | 2.13 |
| active_span_h | behaviour | 1.00 | 0.7478 | 0.5135 | 0.4184 | low | 0.0034 | 1.72 |
| amt_in_max | behaviour | 1.00 | 2,365,343.21 | 193,398.14 | 0.5705 | high | 0.0030 | 1.52 |
| amt_in | behaviour | 1.00 | 2,386,559.49 | 242,939.88 | 0.5685 | high | 0.0030 | 1.48 |
| cyc4 | neighbourhood | 1.00 | 0.0010 | 0.0000 | 0.5005 | high | 0.0029 | 1.45 |
| amt_net | behaviour | 1.00 | -9,707,415.54 | 19,436.70 | 0.5132 | high | 0.0027 | 1.36 |
| cp_in_deg_max | neighbourhood | 1.00 | 1.08 | 0.8494 | 0.5407 | high | 0.0025 | 1.24 |
| fmt_cash_share | behaviour | 1.00 | 0.0315 | 0.0817 | 0.4361 | low | 0.0023 | 1.15 |
| pass_through | graph | 0.9987 | 0.0380 | 0.0194 | 0.5246 | high | 0.0023 | 1.14 |
| fmt_wire_share | behaviour | 1.00 | 0.0042 | 0.0262 | 0.4638 | low | 0.0022 | 1.08 |
| tx_out | behaviour | 1.00 | 62.08 | 1.15 | 0.4728 | low | 0.0022 | 1.08 |
| tx_in | behaviour | 1.00 | 1.90 | 1.27 | 0.4800 | low | 0.0021 | 1.06 |
| hub_neighbours | neighbourhood | 1.00 | 0.1248 | 0.0937 | 0.5155 | high | 0.0021 | 1.04 |
| cp_out_deg_max | neighbourhood | 1.00 | 365.37 | 298.20 | 0.4940 | low | 0.0021 | 1.03 |
| in_amount_hhi | graph | 0.5874 | 0.8404 | 0.9854 | 0.4558 | low | 0.0021 | 1.03 |
| in_out_delay_min_h | graph | 0.2265 | 7.57 | 9.28 | 0.4904 | low | 0.0020 | 1.02 |
| in_out_delay_med_h | graph | 0.2265 | 8.01 | 9.61 | 0.4906 | low | 0.0020 | 1.02 |
| fmt_bitcoin_share | behaviour | 1.00 | 0.0112 | 0.0232 | 0.4940 | low | 0.0020 | 1.01 |
| out_amount_hhi | graph | 0.4949 | 0.9229 | 0.9673 | 0.5123 | high | 0.0020 | 1.01 |
| gs_min_fan | neighbourhood | 1.00 | 0.4009 | 0.3706 | 0.4992 | low | 0.0020 | 1.00 |
| sg_in_max | neighbourhood | 1.00 | 0.1082 | 0.1049 | 0.5015 | high | 0.0020 | 1.00 |
| outside_share | graph | 0.9987 | 0.0000 | 0.0000 | 0.5005 | high | 0.0020 | 1.00 |
| cross_bank_share | graph | 0.9987 | 0.9913 | 0.9921 | 0.4961 | low | 0.0020 | 1.00 |
| unconvertible_share | behaviour | 1.00 | 0.0000 | 0.0000 | 0.5000 | high | 0.0020 | 1.00 |
| fmt_reinvestment_share | behaviour | 1.00 | 0.0000 | 0.0000 | 0.5000 | high | 0.0020 | 1.00 |
| cross_member_share | graph | 0.9987 | 0.8665 | 0.8684 | 0.4684 | low | 0.0020 | 0.9974 |
