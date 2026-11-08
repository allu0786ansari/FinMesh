# Results on the Large sealed tests (A25)

Every rule is the one fixed in `docs/protocol/improvement_plan_A25.md` before the frozen commit. Each run's full page is in `docs/eval/test/`; every opening is in `finmesh sealed-log`. A missed rule is a finding, reported in full.

## HI-Large-W16

| Rule | Test result | Criterion | Holds |
| --- | --- | --- | --- |
| H1a-L | S2 0.534 [0.500, 0.569] vs S0 0.063 [0.046, 0.082]; gain 0.471 [0.433, 0.508], Holm p 0; random-alert linked 0.000 | gain CI excludes 0 (Holm across sharing configurations) and S2 above random | **yes** |
| H1b-L | S2 recovers 0.92 [0.87, 0.97] of the relational oracle's gain (oracle − S0 0.513 [0.476, 0.549]) | ≥ 0.60; reported only if oracle − S0 meets the G1 criterion | **yes** |
| H1c (reported) | S1 and S3 (ε ≤ 2) attacks within the margin of the prior on every assessable target; not assessable: none | upper 95% bound of (attack − prior) TPR at 1% FPR ≤ 0.05 | **yes** |
| H1d-L | PD[tau=2]: gain 0.98 [0.95, 1.01], disclosure 0.32; PD[tau=3]: gain 0.94 [0.91, 0.98], disclosure 0.06; PD[tau=4]: gain 0.95 [0.92, 0.98], disclosure 0.03 | gain share ≥ 0.80 with disclosure < 0.5 of S2's | **yes** (PD[tau=2], PD[tau=3], PD[tau=4]); uninformative: S1, with no record disclosed, already reaches 0.95 of S2's gain (section 6b) |
| Token budget (A16, reported) | peak legitimate use 60,035 (bank 3, epoch 2) vs frozen 109,282; 0 of 16 bank-epochs over; 0.0% of token requests beyond it (served at test) | the A16 sizing holds if no legitimate use exceeds the frozen budget | **yes** |
| H3a (reported) | S2 − S0 attributor 0.019 [-0.001, 0.041]; S2 − majority 0.013 [-0.016, 0.040]; S2 − rules 0.045 [0.017, 0.068] | all three CIs above 0 | **no** |
| Protected flag S1F[gate=2] (reported) | share of plain S1's gain 1.00 [0.98, 1.02]; H1c margin **yes** | chosen on validation (P3); reported on test | reported |
| Case quality (P2, reported) | S2 vs S0: completeness 0.77 vs 0.47, fragmentation 1.05 vs 1.51, time to link (h, median) 0.0 vs 0.0, alerts per linked scheme 18.0 vs 152.6; differences completeness 0.302 [0.280, 0.324]; fragmentation -0.500 [-0.553, -0.446]; time_to_link_h -6.033 [-11.768, -0.832] | reported | reported |
| H1a-L-noart | S2 0.476 [0.439, 0.511] vs S0 0.038 [0.025, 0.053]; gain 0.438 [0.399, 0.474] | gain CI above 0 | **yes** |
| H1a-L+ | S2 0.502 [0.470, 0.538] vs S0 0.069 [0.052, 0.088]; gain 0.433 [0.396, 0.471] | gain CI above 0 | **yes** |
| H1b-L+ | S2 recovers 0.92 [0.86, 0.98] of the relational oracle's gain (oracle − S0 0.470 [0.437, 0.502]) | ≥ 0.60, if oracle − S0 meets the G1 criterion | **yes** |
| H3b (N4, chosen) | grounding 1.000 [0.981, 1.000] over 200 cases; strict (A25N) 0.820 [0.761, 0.867] | raw-reply grounding ≥ 0.95 | **yes** |
| Adaptive budget (P4, reported) | refused, adaptive 6.12% vs frozen 6.12%; PT2 at the adaptive budget 2.59 | not adopted (7 Nov); reported as a design result | reported |

## LI-Large-W16

| Rule | Test result | Criterion | Holds |
| --- | --- | --- | --- |
| H1a-L | S2 0.450 [0.363, 0.539] vs S0 0.067 [0.024, 0.122]; gain 0.383 [0.289, 0.478], Holm p 0; random-alert linked 0.000 | gain CI excludes 0 (Holm across sharing configurations) and S2 above random | **yes** |
| H1b-L | S2 recovers 0.64 [0.52, 0.77] of the relational oracle's gain (oracle − S0 0.593 [0.496, 0.680]) | ≥ 0.60; reported only if oracle − S0 meets the G1 criterion | **yes** |
| H1c (reported) | S1 and S3 (ε ≤ 2) attacks within the margin of the prior on every assessable target; not assessable: none | upper 95% bound of (attack − prior) TPR at 1% FPR ≤ 0.05 | **no** |
| H1d-L | PD[tau=2]: gain 0.81 [0.67, 0.94], disclosure 0.20; PD[tau=3]: gain 0.76 [0.62, 0.88], disclosure 0.01; PD[tau=4]: gain 0.81 [0.67, 0.95], disclosure 0.00 | gain share ≥ 0.80 with disclosure < 0.5 of S2's | **yes** (PD[tau=2], PD[tau=4]) |
| Token budget (A16, reported) | peak legitimate use 48,626 (bank 5, epoch 2) vs frozen 87,926; 0 of 16 bank-epochs over; 0.0% of token requests beyond it (served at test) | the A16 sizing holds if no legitimate use exceeds the frozen budget | **yes** |
| H3a (reported) | S2 − S0 attributor 0.004 [-0.033, 0.043]; S2 − majority 0.058 [0.007, 0.112]; S2 − rules 0.054 [-0.011, 0.123] | all three CIs above 0 | **no** |
| Protected flag S1F[gate=2] (reported) | share of plain S1's gain 0.93 [0.83, 1.03]; H1c margin **yes** | chosen on validation (P3); reported on test | reported |
| Case quality (P2, reported) | S2 vs S0: completeness 0.73 vs 0.48, fragmentation 1.06 vs 1.49, time to link (h, median) 0.0 vs 0.0, alerts per linked scheme 139.5 vs 943.5; differences completeness 0.254 [0.200, 0.310]; fragmentation -0.491 [-0.643, -0.346]; time_to_link_h -9.000 [-27.000, 0.000] | reported | reported |
| H1a-L-noart | S2 0.217 [0.145, 0.290] vs S0 0.007 [0.000, 0.018]; gain 0.210 [0.138, 0.283] | gain CI above 0 | **yes** |
| H1a-L+ | S2 0.420 [0.326, 0.504] vs S0 0.065 [0.022, 0.112]; gain 0.355 [0.246, 0.453] | gain CI above 0 | **yes** |
| H1b-L+ | S2 recovers 0.49 [0.36, 0.61] of the relational oracle's gain (oracle − S0 0.721 [0.634, 0.804]) | ≥ 0.60, if oracle − S0 meets the G1 criterion | **no** |
| H3b (N4, chosen) | grounding 0.951 [0.865, 0.983] over 61 cases; strict (A25N) 0.557 [0.433, 0.675] | raw-reply grounding ≥ 0.95 | **yes** |
| Adaptive budget (P4, reported) | refused, adaptive 4.67% vs frozen 4.67%; PT2 at the adaptive budget 3.2 | not adopted (7 Nov); reported as a design result | reported |
