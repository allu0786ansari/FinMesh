# Protected S1 flags on validation (A25 P3) · HI-Medium

Seeds [0, 1, 2] for linked detection; attacks on seed 0. Share = (candidate − S0) / (plain S1 − S0) in linked detection. Within margin = upper 95% bound of (attack − prior) TPR at 1% FPR ≤ 0.05 on every assessable A2/A3 target.

| Candidate | Linked | Share of S1's gain | Within margin | Per target |
| --- | --- | --- | --- | --- |
| S1 | 0.727 [0.693, 0.759] | 1.000 | yes | A2_third_party: yes, A3_amount_top: yes, A3_fan_in_top: yes, A3_pass_through: yes |
| S1F[eps=0.5] | 0.722 [0.690, 0.755] | 0.991 [0.964, 1.020] | yes | A2_third_party: yes, A3_amount_top: yes, A3_fan_in_top: yes, A3_pass_through: yes |
| S1F[eps=1] | 0.721 [0.689, 0.755] | 0.990 [0.965, 1.017] | yes | A2_third_party: yes, A3_amount_top: yes, A3_fan_in_top: yes, A3_pass_through: yes |
| S1F[eps=2] | 0.719 [0.685, 0.753] | 0.986 [0.962, 1.010] | yes | A2_third_party: yes, A3_amount_top: yes, A3_fan_in_top: yes, A3_pass_through: yes |
| S1F[eps=4] | 0.722 [0.690, 0.756] | 0.992 [0.979, 1.005] | yes | A2_third_party: yes, A3_amount_top: yes, A3_fan_in_top: yes, A3_pass_through: yes |
| S1F[gate=2] | 0.730 [0.698, 0.764] | 1.007 [0.989, 1.025] | yes | A2_third_party: yes, A3_amount_top: yes, A3_fan_in_top: yes, A3_pass_through: yes |
| S1F[gate=3] | 0.730 [0.699, 0.764] | 1.007 [0.986, 1.030] | yes | A2_third_party: yes, A3_amount_top: yes, A3_fan_in_top: yes, A3_pass_through: yes |
| S1F[gate=2,eps=1] | 0.716 [0.682, 0.750] | 0.980 [0.955, 1.008] | yes | A2_third_party: yes, A3_amount_top: yes, A3_fan_in_top: yes, A3_pass_through: yes |
| S1F[gate=2,eps=2] | 0.718 [0.685, 0.753] | 0.985 [0.961, 1.009] | yes | A2_third_party: yes, A3_amount_top: yes, A3_fan_in_top: yes, A3_pass_through: yes |
