# Protocol documents

Frozen documents that later results are judged against. Each is committed and tagged before the results it governs exist.

| Document | Due | Frozen at |
| --- | --- | --- |
| `preregistration.md`: hypotheses, provisional thresholds, metrics, seeds, analysis plan | Week 5 | Gate G1 (tag `g1`) |
| `typology_catalogue.md` and stage mapping, with two review passes | Week 13 | Before any attribution result |
| `split_plan_<dataset>.json`: observation window, 6 h windows, train / val / test periods | Week 3 (`finmesh labels`) | Week 3; checked by `tests/integration/test_real_data_week3.py` |
| `eval_counts_<dataset>.json`: train and validation account-window and scheme counts | Week 3 | Informational |
