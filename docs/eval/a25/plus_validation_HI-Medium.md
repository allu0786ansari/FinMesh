# Stronger-detector track on validation (A25 P6 adequacy) · HI-Medium

Seeds 0,1,2. Linked scheme detection; gain = S2 − S0 (paired, scheme bootstrap); recovery = (S2 − S0) / (relational oracle − S0), as H1b. Token requests: the current detector is metered at the frozen A16 budget; the + track is served in full and its peak is shown against that budget.

| Detector | S0 | S2 | Oracle | Relational oracle | S2 − S0 | Recovery | Candidates (mean) | Peak tokens per bank-epoch |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| + (transaction detector) | 0.179 [0.151, 0.209] | 0.699 [0.664, 0.734] | 0.704 [0.668, 0.741] | 0.739 [0.705, 0.772] | 0.520 [0.479, 0.561] | 0.928 [0.878, 0.979] | 63,119 | 96,263 |
| current (account-window LightGBM) | 0.174 [0.145, 0.203] | 0.736 [0.703, 0.771] | 0.672 [0.636, 0.707] | 0.747 [0.713, 0.782] | 0.562 [0.523, 0.603] | 0.981 [0.936, 1.025] | 71,791 | 42,052 |
