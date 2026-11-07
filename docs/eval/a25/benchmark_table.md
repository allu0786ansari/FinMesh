# Benchmark anchor (A25 P6): minority-class F1 (%), AMLworld split

| Model | HI-Medium | LI-Medium |
| --- | --- | --- |
| A · our pooled detector | 42.67 ± 2.76 | 24.08 ± 2.01 |
| B · transaction LightGBM + our features | 67.01 ± 2.27 | 34.34 ± 1.55 |
| LightGBM + graph features (published) | 59.48 | 20.85 |
| XGBoost + graph features (published) | 65.70 | 28.16 |
| Multi-PNA + EU (published) | 66.48 | 36.07 |

Adequacy (model A, validation F1 vs LightGBM + graph features):

- HI-Medium: -14.45 points — **triggered**
- LI-Medium: +3.07 points
