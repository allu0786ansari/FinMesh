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

## Week 01 · 26 Oct – 1 Nov 2026

Planned: a clean repository with CI, and both datasets loaded, hashed and profiled.
Done: repository layout and tooling; CI with secret scan; transaction loader, pattern parser and scheme linking, accounts loader, SHA-256 manifest, provenance stamps with the fixture gate guard; synthetic fixture; data profile; CLI; scale check; data card, literature matrix, venues note. Details in `docs/runlog/week-01.md`.
Not done: real-data download, ingestion and profiles (the build environment cannot reach Kaggle; steps 5–8 of the run log, on your machine). Venue deadlines: no 2027 calls published yet.
Numbers this week: fixture only (not findings): 18 tests pass, coverage 90%; linking exact on the fixture. Engineering: 5 M synthetic rows ingest in 20 s at 2.6 GB peak.
Risks or blockers: if the real pattern file deviates from the documented block format, linking will report unmatched lines; the parser counts these rather than failing.
Next week: implement the visibility model and per-bank views; count multi-bank schemes for the federation candidates (Gate G0).
On track for next gate? yes, once the real profiles are pushed.
