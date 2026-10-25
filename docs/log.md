# Weekly status log

Newest week first. Template:

```markdown
## Week NN · <dates>

Planned: <the week's goal line>
Done: <ticked items, with artifact paths>
Not done: <items and why>
Numbers this week: <key validation results, with intervals>
Risks or blockers: <what could slip, and which fallback applies>
Next week: <first two tasks>
On track for next gate? yes / at risk / no
```

## Week 06 · 30 Nov – 6 Dec 2026

Planned: banks can match accounts through OPRF tokens and exchange S1 and S2 evidence in the harness.
Done: closed G1 (preregistration frozen; A12 ablation and decomposition added to the baselines runner). Built the token service (per-epoch keys, budgets, count-only log), token client, shared-key hashing control, CC5 contract tests, local autoencoder with top-3 deviations, evidence schema and records, signed one-time requests with rate limits and retention, allowlisted messages and bus, S0/S1/S2 responses, and the in-process protocol run (`finmesh share`). Details in `docs/runlog/week-06.md`.
Not done: real-data protocol run (run-log steps 2–4); the `g1` tag must be pushed from the owner's machine.
Numbers this week: engineering only (hand-built cases, fixture, stress run).
Risks or blockers: S1 should approach the pooled-linking upper bound; if not, the epoch split or the rate limits lose links.
Next week: week 7, fusion, triage, S4 and the first validation frontier.
On track for next gate? yes (G2, week 9).

## Week 05 · 23 – 29 Nov 2026

Planned: the local-only (S0) and pooled-oracle reference points exist, and targets are frozen.
Done: reviewed the week-4 diagnostics; the owner decided A9 (mask incidental positives), A10 (primary operating point 1 alert per 1,000 accounts per day) and A11 (schema v3, 72 h neighbourhood lookback). Built labels with incidental masking, the pooled feature view for the oracle, local and pooled incident linking, a random baseline for linked detection, LightGBM, Isolation Forest and PCA baselines with isotonic calibration, the baselines runner and the G1 evidence page. Drafted the preregistration. Details in `docs/runlog/week-05.md`.
Not done: real-data baselines and G1 evidence (run-log steps 2–6); preregistration section 9 and the `g1` tag follow.
Numbers this week: engineering only (stress set). Member-view features 1,393 s at 3.0 GB; neighbourhood pass made about 1.5x faster, still exact.
Risks or blockers: if the oracle − S0 gap is under 5 points, RQ1's headline needs rethinking before week 6.
Next week: week 6, the evidence-sharing levels.
On track for next gate? yes, pending the G1 run.

G1 (26 Oct, real data): passed. HI-Medium oracle − S0 linked detection 0.508 [0.465, 0.550]; LI-Medium 0.538. The gain is almost all cross-member linking (any-alert detection S0 0.864, oracle 0.886). PT4b direction positive. Thresholds unchanged; artefact ablation and linking decomposition added (A12); preregistration frozen, tag `g1`.

## Week 04 · 16 – 22 Nov 2026

Planned: every account-window at every bank has its behaviour and graph features, within the memory budget.
Done: reviewed the week-3 real-data results (G0 closed on HI-Medium with 480 test schemes; harness calibrated; findings on FPR-budget drift, activity as a top-only signal, scheme coverage, probe grounding). Froze feature schema v1: 47 features (19 behaviour, 12 graph, 5 history, 11 neighbourhood). Built the edge table with data-derived exchange rates, account features in hash slices, member-view neighbourhood features (cycles 2–4, scatter-gather, hub indicators) over a 24 h lookback, and a single-feature report as a leakage smoke test. Label files are now sorted to line up with features. Details in `docs/runlog/week-04.md`.
Not done: real-data build (run-log steps 2–5).
Numbers this week: engineering only. On a 32 M-row heavy-tailed stress set (41 M account-windows): whole build 622 s, peak 2.0 GB (first attempt 5.9 GB; fixed). Feature report 101 s, 1.0 GB.
Risks or blockers: FPR budgets drift between periods; primary operating point to be decided at G1 (recommendation: alerts per 1,000 accounts per day).
Next week: week 5, local and pooled baselines, preregistration, Gate G1.
On track for next gate? yes (G1, week 5).

Follow-up (25 Oct, after the real-data run): history features drifted by construction; replaced by schema v2 before any model (amendment A8). Added `finmesh diagnose`: incidental positives (busy accounts touched once by a scheme), pattern visibility per member, feature drift. Two G1 decisions now pending the diagnostics: primary operating point and the treatment of incidental positives.

## Week 03 · 9 – 15 Nov 2026

Planned: a harness that can score any detector at any budget, with test data locked away.
Done: G0 decided from the week-2 evidence (`docs/gates/G0.md`): headline on HI-Medium with B8 (amendments A5, A6); a bias in my week-2 selection rule found and disclosed; H3b redefined (A7); llama3.2:3b chosen. Built account-window labels with masking, frozen split plans, sealed test entry point with access log, label guard (types plus static check), metrics, per-member budgets with deterministic tie-breaking, scheme detection and linked detection, exact random-alert baseline, bootstrap and Holm. Details in `docs/runlog/week-03.md`.
Not done: real-data run (G0 under A5, labels, harness check, free LLM probe; run-log steps 2–7).
Numbers this week: engineering only. At HI-Medium scale: labels 111 s and 1.3 GB, harness check 163 s and 2.4 GB; random scorer AUPRC 0.001158 against prevalence 0.001164, budgets met per member.
Risks or blockers: none new. HI-Medium account-windows (about 24 M) will need negative subsampling for training (week 5).
Next week: week 4, the graph feature extractor on member views.
On track for next gate? yes (G1, week 5).

## Week 02 · 2 – 8 Nov 2026

Planned: the bank federation is chosen, splits are drafted, and the go/no-go count is known.
Done: CI fixed (lint failure from a week-1 edit) and a local CI mirror added; observation window (dense-period rule, amendment A1), 6 h window rule, 60/20/20 splits with gaps, scheme assignment and masking; visibility model; federation options A (real banks ranked by accounts, amendment A2) and B (grouped institutions); G0 evidence with a selection rule fixed before real numbers; memory-safe data layer for HI-Medium; RFC 9497 OPRF matching Cloudflare's implementation; feature-timing spike; local LLM probe. Details in `docs/runlog/week-02.md`.
Not done: real-data G0 counts, feature timing and LLM probe (owner's machine, run-log steps 3–9); G0 decision note.
Numbers this week: engineering only. At HI-Medium size (32 M synthetic rows): ingest 929 MB (was 5.3 GB), G0 1.2 GB in 78 s. 52 unit tests, coverage 90.5%.
Risks or blockers: G0 likely lands in the case-study or fallback band on the Small sets (week-1 estimate); HI-Medium is ready as the fallback. WSL may have only about 4 GB of RAM; every step now stays under 1.3 GB.
Next week: write the G0 decision from the pushed evidence; then week 3 (sealed test entry point, label guard, metrics, alert budgets, random-alert baseline, bootstrap).
On track for next gate? yes for the gate itself; the RQ1 band is at risk.

## Week 01 · 26 Oct – 1 Nov 2026

Planned: a clean repository with CI, and both datasets loaded, hashed and profiled.
Done: repository layout and tooling; CI with secret scan; transaction loader, pattern parser and scheme linking, accounts loader, SHA-256 manifest, provenance stamps with the fixture gate guard; synthetic fixture; data profile; CLI; scale check; data card, literature matrix, venues note. Details in `docs/runlog/week-01.md`.
Done on real data (24 Oct, owner's machine): HI-Small and LI-Small ingested and profiled; row counts, laundering rates and scheme counts match the published values exactly; all 4,232 pattern lines linked, none ambiguous; peak memory 3.6 GB.
Not done: dataset licence variant; code licence; venue deadlines (no 2027 calls published yet).
Numbers this week: HI-Small 5,078,345 rows, 5,177 laundering, 370 schemes (366 multi-bank), 62% of laundering rows pattern-labelled; LI-Small 6,924,049 rows, 3,565 laundering, 117 schemes, 29% labelled. Dense period 1–10 Sep plus a sparse, about 60%-laundering tail to 17–18 Sep.
Risks or blockers: G0 is at risk. Roughly 70 (HI) and 23 (LI) test schemes exist across all banks, before restricting to federation members; a 4–8 real-bank federation would hold under 4% of accounts. Fallbacks: grouped-institution federation, HI-Medium. See findings in `docs/runlog/week-01.md`.
Next week: visibility model and per-bank views; G0 counts for federation options A, B and C on train and validation schemes; chunked ingestion for HI-Medium.
On track for next gate? at risk; the G0 decision rule already covers this case.
