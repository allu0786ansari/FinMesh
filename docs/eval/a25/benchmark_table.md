# Benchmark anchor (A25 P6): minority-class F1 (%), AMLworld split

| Model | HI-Small | LI-Small | HI-Medium | LI-Medium |
| --- | --- | --- | --- | --- |
| A · our pooled detector | 48.20 ± 0.69 | 23.21 ± 2.80 | 42.67 ± 2.76 | 24.08 ± 2.01 |
| B · transaction LightGBM + our features | 64.25 ± 1.24 | 34.99 ± 1.51 | 67.01 ± 2.27 | 34.34 ± 1.55 |
| LightGBM + graph features (published) | 62.86 | 20.83 | 59.48 | 20.85 |
| XGBoost + graph features (published) | 63.23 | 27.30 | 65.70 | 28.16 |
| Multi-PNA + EU (published) | 68.16 | 33.07 | 66.48 | 36.07 |

Adequacy (model A, validation F1 vs LightGBM + graph features):

- HI-Small: -17.61 points
- LI-Small: +0.60 points
- HI-Medium: -14.45 points — **triggered**
- LI-Medium: +3.07 points
