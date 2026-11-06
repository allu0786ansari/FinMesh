# Results on the sealed test (week 18)

Every rule below is the pre-registered one (`docs/protocol/preregistration.md`, amendments in `docs/proposal/CHANGES.md`), and the run order and openings are those of `docs/protocol/test_plan.md`. Each run's full page is next to this one; every opening is in `finmesh sealed-log`. A missed target is a finding, reported in full.

## HI-Medium

| Hypothesis | Test result | Rule | Holds |
| --- | --- | --- | --- |
| H1a (primary on HI-Medium) | S2 0.702 [0.666, 0.737] vs S0 0.136 [0.110, 0.162]; gain 0.566 [0.529, 0.606], Holm p 0; random-alert linked 0.000 | gain CI excludes 0 (Holm across sharing configurations) and S2 above random | **yes** |
| H1b | S2 recovers 0.98 [0.94, 1.03] of the relational oracle's gain (oracle − S0 0.578 [0.540, 0.617]) | ≥ 0.60; reported only if oracle − S0 meets the G1 criterion | **yes** |
| H1c | S1 and S3 (ε ≤ 2) attacks within the margin of the prior on every assessable target; not assessable: none | upper 95% bound of (attack − prior) TPR at 1% FPR ≤ 0.05 | **yes** |
| H1d | PD[tau=2]: gain 1.00 [0.98, 1.01], disclosure 0.31; PD[tau=3]: gain 1.00 [0.98, 1.02], disclosure 0.11; PD[tau=4]: gain 0.98 [0.96, 0.99], disclosure 0.07 | gain share ≥ 0.80 with disclosure < 0.5 of S2's | **yes** (PD[tau=2], PD[tau=3], PD[tau=4]) |
| Token budget (A16, reported) | peak legitimate use 168,913 (bank 7, epoch 2) vs frozen 74,510; 2 of 16 bank-epochs over; 18.8% of token requests beyond it (served at test) | the A16 sizing holds if no legitimate use exceeds the frozen budget | **no** |
| H3a | S2 − S0 attributor 0.044 [0.021, 0.067]; S2 − majority 0.076 [0.044, 0.105]; S2 − rules 0.061 [0.027, 0.095] | all three CIs above 0 | **yes** |
| PT4b | S0-BG − S0-B AUPRC 0.0149 [0.0085, 0.0213] | CI excludes 0 | **yes** |
| Artefact ablation | oracle − S0 linked 0.458 [0.410, 0.508] with the artefact features, 0.372 [0.332, 0.416] without | reported (section 8) | reported |
| H2a | ε 1: share 0.55 [0.53, 0.58], − local -0.0418 [-0.0485, -0.0353]; ε 3: share 0.70 [0.67, 0.72], − local -0.0156 [-0.0216, -0.0095]; ε 10: share 0.73 [0.71, 0.76], − local -0.0083 [-0.0138, -0.0029] | ≥ 0.70 of centralised AUPRC and above local-only, at ε ≤ 10 | **no** |
| H2b | ε 1: window − account -0.0281 [-0.0326, -0.0238]; ε 3: window − account -0.0068 [-0.0103, -0.0033]; ε 10: window − account -0.0076 [-0.0111, -0.0041] | window − account AUPRC CI above 0 at the same ε | **no** |
| Ensemble (G3 rule, reported) | dp1 0.0039 [0.0029, 0.0048]; dp3 0.0041 [0.0031, 0.0050]; dp10 0.0049 [0.0037, 0.0059]; fedavg 0.0161 [0.0142, 0.0179]; centralised 0.0232 [0.0206, 0.0256] | smallest ε ≤ 10 with gain CI above 0 | ε = 1 |
| H3b | grounding 0.860 [0.805, 0.901] over 200 cases; strict (A23) 0.145 [0.103, 0.200]; S2 top-3 0.422 [0.378, 0.466] | raw-reply grounding ≥ 0.95 | **no** |

## LI-Medium

| Hypothesis | Test result | Rule | Holds |
| --- | --- | --- | --- |
| H1a (primary on HI-Medium) | S2 0.657 [0.568, 0.743] vs S0 0.109 [0.057, 0.172]; gain 0.549 [0.449, 0.634], Holm p 0; random-alert linked 0.000 | gain CI excludes 0 (Holm across sharing configurations) and S2 above random | **yes** |
| H1b | S2 recovers 0.79 [0.69, 0.88] of the relational oracle's gain (oracle − S0 0.696 [0.615, 0.770]) | ≥ 0.60; reported only if oracle − S0 meets the G1 criterion | **yes** |
| H1c | S1 and S3 (ε ≤ 2) attacks within the margin of the prior on every assessable target; not assessable: none | upper 95% bound of (attack − prior) TPR at 1% FPR ≤ 0.05 | **no** |
| H1d | PD[tau=2]: gain 0.95 [0.91, 0.98], disclosure 0.18; PD[tau=3]: gain 0.94 [0.88, 0.99], disclosure 0.02; PD[tau=4]: gain 0.99 [0.95, 1.03], disclosure 0.01 | gain share ≥ 0.80 with disclosure < 0.5 of S2's | **yes** (PD[tau=2], PD[tau=3], PD[tau=4]) |
| Token budget (A16, reported) | peak legitimate use 46,634 (bank 0, epoch 2) vs frozen 87,580; 0 of 16 bank-epochs over; 0.0% of token requests beyond it (served at test) | the A16 sizing holds if no legitimate use exceeds the frozen budget | **yes** |
| H3a | S2 − S0 attributor 0.028 [-0.046, 0.089]; S2 − majority 0.103 [0.018, 0.181]; S2 − rules 0.145 [0.071, 0.220] | all three CIs above 0 | **no** |
| PT4b | S0-BG − S0-B AUPRC 0.0104 [0.0056, 0.0155] | CI excludes 0 | **yes** |
| Artefact ablation | oracle − S0 linked 0.500 [0.394, 0.596] with the artefact features, 0.319 [0.223, 0.415] without | reported (section 8) | reported |
| H2a | ε 1: share 0.61 [0.57, 0.65], − local -0.0029 [-0.0056, -0.0003]; ε 3: share 0.77 [0.73, 0.82], − local 0.0065 [0.0034, 0.0098]; ε 10: share 0.86 [0.82, 0.91], − local 0.0118 [0.0078, 0.0158] | ≥ 0.70 of centralised AUPRC and above local-only, at ε ≤ 10 | **yes** (ε 3, 10) |
| H2b | ε 1: window − account 0.0076 [0.0050, 0.0111]; ε 3: window − account 0.0053 [0.0029, 0.0081]; ε 10: window − account 0.0038 [0.0018, 0.0061] | window − account AUPRC CI above 0 at the same ε | **yes** (ε 1, 3, 10) |
| Ensemble (G3 rule, reported) | dp1 0.0019 [0.0008, 0.0028]; dp3 0.0035 [0.0024, 0.0046]; dp10 0.0041 [0.0026, 0.0057]; fedavg 0.0044 [0.0025, 0.0067]; centralised 0.0078 [0.0055, 0.0103] | smallest ε ≤ 10 with gain CI above 0 | ε = 1 |
| H3b | grounding 0.921 [0.838, 0.963] over 76 cases; strict (A23) 0.118 [0.064, 0.210]; S2 top-3 0.330 [0.234, 0.426] | raw-reply grounding ≥ 0.95 | **no** |

## HI-Small

| Hypothesis | Test result | Rule | Holds |
| --- | --- | --- | --- |
| H1a (primary on HI-Medium) | S2 0.613 [0.516, 0.704] vs S0 0.081 [0.030, 0.139]; gain 0.532 [0.425, 0.636], Holm p 0; random-alert linked 0.000 | gain CI excludes 0 (Holm across sharing configurations) and S2 above random | **yes** |
| H1b | S2 recovers 0.84 [0.72, 0.95] of the relational oracle's gain (oracle − S0 0.635 [0.547, 0.717]) | ≥ 0.60; reported only if oracle − S0 meets the G1 criterion | **yes** |
| H1d | PD[tau=2]: gain 0.99 [0.93, 1.04], disclosure 0.43; PD[tau=3]: gain 0.95 [0.87, 1.05], disclosure 0.08; PD[tau=4]: gain 0.90 [0.82, 1.00], disclosure 0.02 | gain share ≥ 0.80 with disclosure < 0.5 of S2's | **yes** (PD[tau=2], PD[tau=3], PD[tau=4]) |
| Token budget (A16, reported) | peak legitimate use 24,391 (bank 4, epoch 1) vs frozen 250,000; 0 of 8 bank-epochs over; 0.0% of token requests beyond it (served at test) | the A16 sizing holds if no legitimate use exceeds the frozen budget | **yes** |

## LI-Small

| Hypothesis | Test result | Rule | Holds |
| --- | --- | --- | --- |
| H1a (primary on HI-Medium) | S2 0.322 [0.167, 0.489] vs S0 0.067 [0.000, 0.189]; gain 0.256 [0.111, 0.400], Holm p 0; random-alert linked 0.000 | gain CI excludes 0 (Holm across sharing configurations) and S2 above random | **yes** |
| H1b | S2 recovers 0.47 [0.24, 0.70] of the relational oracle's gain (oracle − S0 0.544 [0.344, 0.756]) | ≥ 0.60; reported only if oracle − S0 meets the G1 criterion | **no** |
| H1d | PD[tau=2]: gain 0.96 [0.75, 1.11], disclosure 0.20; PD[tau=3]: gain 0.78 [0.48, 1.00], disclosure 0.01; PD[tau=4]: gain 0.91 [0.67, 1.14], disclosure 0.00 | gain share ≥ 0.80 with disclosure < 0.5 of S2's | **yes** (PD[tau=2], PD[tau=4]) |
| Token budget (A16, reported) | peak legitimate use 28,738 (bank 4, epoch 1) vs frozen 250,000; 0 of 8 bank-epochs over; 0.0% of token requests beyond it (served at test) | the A16 sizing holds if no legitimate use exceeds the frozen budget | **yes** |
