# Single-feature signal · HI-Small

Federation B8, feature schema v1, val partition: 707,997 account-windows, 1,150 positive (prevalence 0.0016). Each feature alone ranks the account-windows; AUPRC uses the better direction, chosen on these same rows, so the table is descriptive. Lift = AUPRC / prevalence.

**Leakage check:** no feature reaches AUROC 0.95 or AUPRC 0.5 on its own.

| Feature | Family | Present | Mean (positive) | Mean (negative) | AUROC | Better | AUPRC | Lift |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fan_out | graph | 1.00 | 34.09 | 0.6094 | 0.5458 | high | 0.0388 | 23.91 |
| nb_out_deg | neighbourhood | 1.00 | 112.59 | 1.27 | 0.5140 | high | 0.0384 | 23.63 |
| sg_out_max | neighbourhood | 1.00 | 0.2061 | 0.1310 | 0.5217 | high | 0.0206 | 12.66 |
| fmt_ach_share | behaviour | 1.00 | 0.6959 | 0.1072 | 0.8541 | high | 0.0198 | 12.22 |
| new_cp_n | graph | 1.00 | 1.43 | 0.1005 | 0.8114 | high | 0.0157 | 9.65 |
| amt_vs_history | history | 0.9984 | 0.4418 | -1.56 | 0.6563 | high | 0.0115 | 7.06 |
| legs_vs_history | history | 0.9984 | 0.6188 | 0.4494 | 0.5643 | high | 0.0095 | 5.82 |
| new_cp_share | graph | 0.9982 | 0.5910 | 0.0703 | 0.8054 | high | 0.0094 | 5.79 |
| amt_out | behaviour | 1.00 | 11,689,473.87 | 281,664.64 | 0.5710 | high | 0.0090 | 5.56 |
| prior_active_windows | history | 1.00 | 8.97 | 11.12 | 0.3612 | low | 0.0072 | 4.41 |
| prior_leg_rate | history | 0.9984 | 62.86 | 1.28 | 0.3656 | low | 0.0070 | 4.29 |
| currencies_n | behaviour | 1.00 | 1.13 | 1.01 | 0.5567 | high | 0.0068 | 4.16 |
| fan_in | graph | 1.00 | 1.44 | 0.6626 | 0.5510 | high | 0.0066 | 4.06 |
| cyc2 | neighbourhood | 1.00 | 0.0409 | 0.0005 | 0.5193 | high | 0.0062 | 3.81 |
| fmt_cheque_share | behaviour | 1.00 | 0.1387 | 0.4462 | 0.1791 | low | 0.0061 | 3.78 |
| nb_in_deg | neighbourhood | 1.00 | 1.81 | 1.05 | 0.5510 | high | 0.0052 | 3.20 |
| amt_out_max | behaviour | 1.00 | 3,254,514.43 | 229,794.17 | 0.5784 | high | 0.0049 | 2.99 |
| cross_currency_share | behaviour | 1.00 | 0.0667 | 0.0060 | 0.5565 | high | 0.0036 | 2.24 |
| fmt_credit_card_share | behaviour | 1.00 | 0.0886 | 0.3032 | 0.2675 | low | 0.0032 | 1.95 |
| self_tx | behaviour | 1.00 | 0.1435 | 0.0287 | 0.5553 | high | 0.0031 | 1.91 |
| active_span_h | behaviour | 1.00 | 1.05 | 0.5807 | 0.4638 | low | 0.0025 | 1.56 |
| amt_in_max | behaviour | 1.00 | 812,442.62 | 245,827.71 | 0.5724 | high | 0.0023 | 1.40 |
| amt_in | behaviour | 1.00 | 831,306.23 | 299,362.59 | 0.5702 | high | 0.0022 | 1.38 |
| cp_in_deg_max | neighbourhood | 1.00 | 1.11 | 0.9105 | 0.5442 | high | 0.0021 | 1.30 |
| amt_net | behaviour | 1.00 | -10,858,167.65 | 17,697.95 | 0.5010 | high | 0.0020 | 1.23 |
| pass_through | graph | 0.9982 | 0.0460 | 0.0226 | 0.5346 | high | 0.0020 | 1.22 |
| age_windows | history | 1.00 | 25.92 | 26.18 | 0.5186 | high | 0.0018 | 1.11 |
| hub_neighbours | neighbourhood | 1.00 | 0.1583 | 0.1025 | 0.5279 | high | 0.0018 | 1.09 |
| fmt_wire_share | behaviour | 1.00 | 0.0047 | 0.0274 | 0.4620 | low | 0.0018 | 1.08 |
| fmt_cash_share | behaviour | 1.00 | 0.0512 | 0.0848 | 0.4647 | low | 0.0017 | 1.07 |
| tx_in | behaviour | 1.00 | 1.77 | 1.33 | 0.4865 | low | 0.0017 | 1.04 |
| cp_out_deg_max | neighbourhood | 1.00 | 199.28 | 113.18 | 0.4982 | low | 0.0017 | 1.03 |
| tx_out | behaviour | 1.00 | 67.34 | 1.23 | 0.4939 | low | 0.0017 | 1.03 |
| in_amount_hhi | graph | 0.6034 | 0.8638 | 0.9845 | 0.4620 | low | 0.0017 | 1.02 |
| fmt_bitcoin_share | behaviour | 1.00 | 0.0209 | 0.0312 | 0.4948 | low | 0.0016 | 1.01 |
| in_out_delay_min_h | graph | 0.2857 | 7.77 | 9.47 | 0.4926 | low | 0.0016 | 1.01 |
| in_out_delay_med_h | graph | 0.2857 | 8.32 | 9.83 | 0.4933 | low | 0.0016 | 1.01 |
| gs_min_fan | neighbourhood | 1.00 | 0.4896 | 0.4769 | 0.4975 | low | 0.0016 | 1.01 |
| outside_share | graph | 0.9982 | 0.0000 | 0.0000 | 0.5009 | high | 0.0016 | 1.00 |
| sg_in_max | neighbourhood | 1.00 | 0.1504 | 0.1490 | 0.5008 | high | 0.0016 | 1.00 |
| unconvertible_share | behaviour | 1.00 | 0.0000 | 0.0000 | 0.5000 | high | 0.0016 | 1.00 |
| fmt_reinvestment_share | behaviour | 1.00 | 0.0000 | 0.0000 | 0.5000 | high | 0.0016 | 1.00 |
| cyc3 | neighbourhood | 1.00 | 0.0000 | 0.0000 | 0.5000 | high | 0.0016 | 1.00 |
| cyc4 | neighbourhood | 1.00 | 0.0000 | 0.0000 | 0.5000 | high | 0.0016 | 1.00 |
| cross_bank_share | graph | 0.9982 | 0.9770 | 0.9778 | 0.4945 | low | 0.0016 | 0.9991 |
| cross_member_share | graph | 0.9982 | 0.8674 | 0.8602 | 0.4680 | low | 0.0016 | 0.9901 |
| out_amount_hhi | graph | 0.4929 | 0.8754 | 0.9614 | 0.5080 | high | 0.0016 | 0.9791 |
