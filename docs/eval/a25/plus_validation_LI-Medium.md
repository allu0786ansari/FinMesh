# Stronger-detector track on validation (A25 P6 adequacy) · LI-Medium

Seeds 0,1,2. Linked scheme detection; gain = S2 − S0 (paired, scheme bootstrap); recovery = (S2 − S0) / (relational oracle − S0), as H1b. Token requests: the current detector is metered at the frozen A16 budget; the + track is served in full and its peak is shown against that budget.

| Detector | S0 | S2 | Oracle | Relational oracle | S2 − S0 | Recovery | Candidates (mean) | Peak tokens per bank-epoch |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| + (transaction detector) | 0.168 [0.104, 0.237] | 0.703 [0.627, 0.781] | 0.803 [0.728, 0.871] | 0.778 [0.695, 0.853] | 0.534 [0.448, 0.627] | 0.876 [0.787, 0.975] | 59,977 | 30,266 |
| current (account-window LightGBM) | 0.154 [0.090, 0.219] | 0.695 [0.609, 0.778] | 0.703 [0.616, 0.789] | 0.806 [0.731, 0.878] | 0.541 [0.448, 0.638] | 0.830 [0.737, 0.921] | 65,238 | 43,790 |
