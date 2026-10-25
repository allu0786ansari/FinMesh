# Single-feature signal · LI-Medium

Federation B8, feature schema v2, val partition: 3,324,357 account-windows, 4,433 positive (prevalence 0.0013). Each feature alone ranks the account-windows; AUPRC uses the better direction, chosen on these same rows, so the table is descriptive. Lift = AUPRC / prevalence.

**Leakage check:** no feature reaches AUROC 0.95 or AUPRC 0.5 on its own.

| Feature | Family | Present | Mean (positive) | Mean (negative) | AUROC | Better | AUPRC | Lift |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fan_out | graph | 1.00 | 46.61 | 0.5859 | 0.5020 | high | 0.0301 | 22.60 |
| new_cp_n | graph | 1.00 | 6.68 | 0.2503 | 0.7949 | high | 0.0243 | 18.20 |
| fmt_ach_share | behaviour | 1.00 | 0.7459 | 0.1140 | 0.8565 | high | 0.0158 | 11.87 |
| fan_in | graph | 1.00 | 2.15 | 0.6453 | 0.5625 | high | 0.0111 | 8.30 |
| nb_in_deg | neighbourhood | 1.00 | 2.35 | 0.9306 | 0.5436 | high | 0.0089 | 6.66 |
| legs_vs_history | history | 1.00 | 0.7991 | 0.6027 | 0.5647 | high | 0.0077 | 5.77 |
| amt_out | behaviour | 1.00 | 15,867,444.37 | 252,311.48 | 0.5284 | high | 0.0075 | 5.64 |
| amt_vs_history | history | 1.00 | 3.74 | 0.5990 | 0.7243 | high | 0.0069 | 5.21 |
| tx_in | behaviour | 1.00 | 2.40 | 1.27 | 0.5053 | high | 0.0065 | 4.90 |
| fmt_cheque_share | behaviour | 1.00 | 0.1250 | 0.4373 | 0.1857 | low | 0.0051 | 3.83 |
| prior_leg_rate | history | 1.00 | 86.77 | 0.8926 | 0.2984 | low | 0.0043 | 3.24 |
| new_cp_share | graph | 0.9987 | 0.7075 | 0.1911 | 0.7799 | high | 0.0041 | 3.09 |
| prior_active_windows | history | 1.00 | 2.47 | 3.96 | 0.2976 | low | 0.0039 | 2.94 |
| recency_windows | history | 1.00 | 6.49 | 3.74 | 0.6543 | high | 0.0039 | 2.89 |
| amt_out_max | behaviour | 1.00 | 4,762,744.98 | 201,531.17 | 0.5376 | high | 0.0038 | 2.83 |
| fmt_credit_card_share | behaviour | 1.00 | 0.0736 | 0.3188 | 0.2487 | low | 0.0029 | 2.16 |
| active_span_h | behaviour | 1.00 | 0.6191 | 0.5138 | 0.4115 | low | 0.0022 | 1.67 |
| amt_in_max | behaviour | 1.00 | 3,021,584.58 | 215,507.55 | 0.5590 | high | 0.0021 | 1.56 |
| amt_in | behaviour | 1.00 | 3,099,262.09 | 269,358.33 | 0.5606 | high | 0.0021 | 1.56 |
| amt_net | behaviour | 1.00 | -12,768,182.29 | 17,046.85 | 0.5310 | high | 0.0020 | 1.51 |
| cyc2 | neighbourhood | 1.00 | 0.0158 | 0.0006 | 0.5075 | high | 0.0018 | 1.39 |
| cp_in_deg_max | neighbourhood | 1.00 | 1.11 | 0.8557 | 0.5155 | high | 0.0017 | 1.26 |
| currencies_n | behaviour | 1.00 | 1.04 | 1.01 | 0.5134 | high | 0.0016 | 1.17 |
| tx_out | behaviour | 1.00 | 91.72 | 1.16 | 0.4467 | low | 0.0015 | 1.15 |
| fmt_cash_share | behaviour | 1.00 | 0.0357 | 0.0816 | 0.4391 | low | 0.0015 | 1.14 |
| hub_neighbours | neighbourhood | 1.00 | 0.1633 | 0.0937 | 0.5348 | high | 0.0015 | 1.12 |
| cross_currency_share | behaviour | 1.00 | 0.0218 | 0.0060 | 0.5133 | high | 0.0015 | 1.11 |
| gs_min_fan | neighbourhood | 1.00 | 0.2642 | 0.3701 | 0.4511 | low | 0.0015 | 1.11 |
| in_out_delay_med_h | graph | 0.2262 | 8.38 | 9.61 | 0.4609 | low | 0.0015 | 1.09 |
| in_out_delay_min_h | graph | 0.2262 | 8.16 | 9.28 | 0.4612 | low | 0.0015 | 1.09 |
| fmt_wire_share | behaviour | 1.00 | 0.0028 | 0.0265 | 0.4594 | low | 0.0015 | 1.09 |
| nb_out_deg | neighbourhood | 1.00 | 142.25 | 1.06 | 0.4641 | low | 0.0014 | 1.08 |
| cp_out_deg_max | neighbourhood | 1.00 | 534.94 | 309.35 | 0.4832 | low | 0.0014 | 1.07 |
| self_tx | behaviour | 1.00 | 0.0408 | 0.0250 | 0.5124 | high | 0.0014 | 1.07 |
| in_amount_hhi | graph | 0.5869 | 0.7881 | 0.9852 | 0.4408 | low | 0.0014 | 1.06 |
| pass_through | graph | 0.9987 | 0.0232 | 0.0192 | 0.5027 | high | 0.0014 | 1.03 |
| sg_in_max | neighbourhood | 1.00 | 0.0812 | 0.1045 | 0.4884 | low | 0.0014 | 1.02 |
| sg_out_max | neighbourhood | 1.00 | 0.0993 | 0.0930 | 0.4959 | low | 0.0013 | 1.01 |
| fmt_bitcoin_share | behaviour | 1.00 | 0.0169 | 0.0217 | 0.4976 | low | 0.0013 | 1.00 |
| outside_share | graph | 0.9987 | 0.0000 | 0.0000 | 0.5007 | high | 0.0013 | 1.00 |
| out_amount_hhi | graph | 0.4951 | 0.9241 | 0.9673 | 0.4991 | low | 0.0013 | 1.00 |
| cyc3 | neighbourhood | 1.00 | 0.0000 | 0.0000 | 0.5000 | low | 0.0013 | 1.00 |
| unconvertible_share | behaviour | 1.00 | 0.0000 | 0.0000 | 0.5000 | high | 0.0013 | 1.00 |
| fmt_reinvestment_share | behaviour | 1.00 | 0.0000 | 0.0000 | 0.5000 | high | 0.0013 | 1.00 |
| cyc4 | neighbourhood | 1.00 | 0.0000 | 0.0000 | 0.5000 | high | 0.0013 | 1.00 |
| cross_bank_share | graph | 0.9987 | 0.9926 | 0.9924 | 0.4966 | low | 0.0013 | 0.9996 |
| cross_member_share | graph | 0.9987 | 0.8724 | 0.8689 | 0.4646 | low | 0.0013 | 0.9982 |
