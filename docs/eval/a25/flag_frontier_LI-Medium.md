# Protected S1 flags on validation (A25 P3) · LI-Medium

Seeds [0, 1, 2] for linked detection; attacks on seed 0. Share = (candidate − S0) / (plain S1 − S0) in linked detection. Within margin = upper 95% bound of (attack − prior) TPR at 1% FPR ≤ 0.05 on every assessable A2/A3 target.

| Candidate | Linked | Share of S1's gain | Within margin | Per target |
| --- | --- | --- | --- | --- |
| S1 | 0.663 [0.577, 0.746] | 1.000 | no | A2_third_party: yes, A3_amount_top: yes, A3_fan_in_top: no, A3_pass_through: yes |
| S1F[eps=0.5] | 0.656 [0.570, 0.738] | 0.986 [0.938, 1.033] | yes | A2_third_party: yes, A3_amount_top: yes, A3_fan_in_top: yes, A3_pass_through: yes |
| S1F[eps=1] | 0.652 [0.563, 0.735] | 0.979 [0.924, 1.031] | yes | A2_third_party: yes, A3_amount_top: yes, A3_fan_in_top: yes, A3_pass_through: yes |
| S1F[eps=2] | 0.652 [0.559, 0.738] | 0.979 [0.917, 1.043] | yes | A2_third_party: yes, A3_amount_top: yes, A3_fan_in_top: yes, A3_pass_through: yes |
| S1F[eps=4] | 0.663 [0.577, 0.746] | 1.000 [0.958, 1.036] | yes | A2_third_party: yes, A3_amount_top: yes, A3_fan_in_top: yes, A3_pass_through: yes |
| S1F[gate=2] | 0.670 [0.581, 0.753] | 1.014 [0.961, 1.067] | yes | A2_third_party: yes, A3_amount_top: yes, A3_fan_in_top: yes, A3_pass_through: yes |
| S1F[gate=3] | 0.649 [0.563, 0.731] | 0.972 [0.920, 1.020] | yes | A2_third_party: yes, A3_amount_top: yes, A3_fan_in_top: yes, A3_pass_through: yes |
| S1F[gate=2,eps=1] | 0.652 [0.566, 0.735] | 0.979 [0.924, 1.030] | yes | A2_third_party: yes, A3_amount_top: yes, A3_fan_in_top: yes, A3_pass_through: yes |
| S1F[gate=2,eps=2] | 0.652 [0.563, 0.735] | 0.979 [0.926, 1.031] | yes | A2_third_party: yes, A3_amount_top: yes, A3_fan_in_top: yes, A3_pass_through: yes |
