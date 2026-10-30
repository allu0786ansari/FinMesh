# DP hyperparameters on the proxy federation · HI-Small

Amendment A18: FedAvg with DP-SGD at ε = 3 (window unit, seed 0, lr 0.001, 50 rounds; local steps per round = 20 × 512 / batch, so every setting sees the same number of examples) for every clip norm and expected batch in the grid, scored by AUPRC on this federation's training hold-out (18,815 rows, 417 positives). The best setting is written to `finmesh/schemas/dp_hparams.json` and used unchanged on the Medium set of the same regime; no Medium data is used here. Total 690 s, peak memory 551 MB.

| Clip norm | Expected batch | Local steps per round | Hold-out AUPRC | Share clipped | Noise multiplier | Seconds |
| --- | --- | --- | --- | --- | --- | --- |
| 0.0100 | 512 | 20 | 0.2821 | 0.0464 | 3.56 | 50.60 |
| 0.0100 | 2,048 | 5 | 0.1282 | 0.0882 | 6.98 | 52.50 |
| 0.0100 | 8,192 | 1 | 0.0248 | 0.2944 | 10.38 | 32.00 |
| 0.0300 | 512 | 20 | 0.3093 | 0.0434 | 3.56 | 51.20 |
| 0.0300 | 2,048 | 5 | 0.1480 | 0.0796 | 6.98 | 46.50 |
| 0.0300 | 8,192 | 1 | 0.0274 | 0.2589 | 10.38 | 32.50 |
| 0.1000 | 512 | 20 | 0.3403 | 0.0398 | 3.56 | 52.40 |
| 0.1000 | 2,048 | 5 | 0.1736 | 0.0694 | 6.98 | 49.90 |
| 0.1000 | 8,192 | 1 | 0.0325 | 0.2159 | 10.38 | 36.30 |
| 0.3000 | 512 | 20 | 0.3719 | 0.0366 | 3.56 | 53.60 |
| 0.3000 | 2,048 | 5 | 0.2016 | 0.0590 | 6.98 | 59.50 |
| 0.3000 | 8,192 | 1 | 0.0421 | 0.1708 | 10.38 | 39.40 |
| 1.00 | 512 | 20 | 0.4158 | 0.0322 | 3.56 | 52.60 |
| 1.00 | 2,048 | 5 | 0.2395 | 0.0453 | 6.98 | 48.20 |
| 1.00 | 8,192 | 1 | 0.0673 | 0.1105 | 10.38 | 32.20 |

**Chosen:** clip 1, expected batch 512, 20 local steps per round, hold-out AUPRC 0.4158.
