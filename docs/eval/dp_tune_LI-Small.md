# DP hyperparameters on the proxy federation · LI-Small

Amendment A18: FedAvg with DP-SGD at ε = 3 (window unit, seed 0, lr 0.001, 50 rounds; local steps per round = 20 × 512 / batch, so every setting sees the same number of examples) for every clip norm and expected batch in the grid, scored by AUPRC on this federation's training hold-out (25,362 rows, 288 positives). The best setting is written to `finmesh/schemas/dp_hparams.json` and used unchanged on the Medium set of the same regime; no Medium data is used here. Total 690 s, peak memory 586 MB.

| Clip norm | Expected batch | Local steps per round | Hold-out AUPRC | Share clipped | Noise multiplier | Seconds |
| --- | --- | --- | --- | --- | --- | --- |
| 0.0100 | 512 | 20 | 0.0952 | 0.0329 | 2.75 | 49.60 |
| 0.0100 | 2,048 | 5 | 0.0421 | 0.0738 | 5.34 | 46.30 |
| 0.0100 | 8,192 | 1 | 0.0114 | 0.2783 | 9.34 | 41.50 |
| 0.0300 | 512 | 20 | 0.1046 | 0.0302 | 2.75 | 49.10 |
| 0.0300 | 2,048 | 5 | 0.0496 | 0.0657 | 5.34 | 46.10 |
| 0.0300 | 8,192 | 1 | 0.0123 | 0.2435 | 9.34 | 43.10 |
| 0.1000 | 512 | 20 | 0.1162 | 0.0272 | 2.75 | 48.10 |
| 0.1000 | 2,048 | 5 | 0.0594 | 0.0560 | 5.34 | 45.40 |
| 0.1000 | 8,192 | 1 | 0.0136 | 0.2013 | 9.34 | 46.60 |
| 0.3000 | 512 | 20 | 0.1313 | 0.0243 | 2.75 | 48.60 |
| 0.3000 | 2,048 | 5 | 0.0712 | 0.0464 | 5.34 | 45.50 |
| 0.3000 | 8,192 | 1 | 0.0159 | 0.1573 | 9.34 | 43.50 |
| 1.00 | 512 | 20 | 0.1505 | 0.0205 | 2.75 | 47.80 |
| 1.00 | 2,048 | 5 | 0.0883 | 0.0332 | 5.34 | 45.80 |
| 1.00 | 8,192 | 1 | 0.0220 | 0.0981 | 9.34 | 42.60 |

**Chosen:** clip 1, expected batch 512, 20 local steps per round, hold-out AUPRC 0.1505.
