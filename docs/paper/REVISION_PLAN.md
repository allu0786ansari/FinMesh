# Revision plan (section-by-section review, Nov 2026)

Changes agreed in the review, to be applied together at the end and compiled on Overleaf. Each item says what to change and why; the replacement text is given where it is more than a word. Status: **pending** until applied.

## 1. Abstract and Index Terms (reviewed 12 Nov)

| # | Change | Reason |
| --- | --- | --- |
| A1 | "without reducing detection" → "while keeping 93–100% of the flag's detection gain" | LI-Large keeps 0.93 [0.83, 1.03] of S1's gain (`RESULTS_LARGE.md`) |
| A2 | Name the stronger detector exactly: "a per-bank version of a transaction-level detector that outperforms published gradient-boosting results" | The pooled transaction model beats the baselines; S0+ is its per-bank version |
| A3 | Say the benchmark is synthetic: "the synthetic AMLworld benchmark" | Reviewers should see it at once |
| A4 | Quantify the misses: attribution "did not replicate on the fresh windows"; OPRF "reduced re-identification 8 to 9 times relative to hashing, short of the tenfold target" | H3a met on HI-Medium only; PT2 8.1, 9.3, 8.7 (missed), 19.9 (met) |
| A5 | "6.8 to 8.5 times fewer alerts" → add "On the fresh windows" | Those ratios are from the two Large tests |
| A6 | "We evaluate" → "We design and evaluate a privacy-preserving protocol"; "positive" → "significant" | Matches the title; CIs exclude 0 after Holm |
| A7 | Index Terms in alphabetical order | IEEE style |

Replacement abstract and Index Terms:

```latex
\begin{abstract}
A laundering scheme usually touches several banks, and each bank's monitoring sees only
its own part of it. We design and evaluate a privacy-preserving protocol in which banks
answer each other's queries with minimised evidence about counterparty accounts (an alert
flag, a probability bucket and bucketed behaviour counters), addressed by tokens from an
oblivious pseudorandom function. All hypotheses were pre-registered and decided once on
sealed test data from the synthetic AMLworld benchmark; improvements made afterwards were
confirmed on two further test windows that had never been opened. On the unopened
high-illicit window, sharing raised the share of laundering schemes linked into one case
from 0.063 to 0.534 (gain 0.47, 95\% CI [0.43, 0.51]), recovering 0.92 of the gain of a
pooled relational model. The gain was significant on all four sealed tests, persisted
without the suspected simulator artefacts, and persisted with a per-bank version of a
transaction-level detector that outperforms published gradient-boosting results on
AMLworld. On the fresh windows, analysts reviewed 6.8 to 8.5 times fewer alerts per linked
scheme. An attack-based leakage audit found that the plain alert flag reveals high fan-in
in the low-illicit data; a gated flag selected on validation removed this leakage on fresh
data while keeping 93--100\% of the flag's detection gain. Typology attribution did not
replicate on the fresh windows, and the oblivious tokens reduced re-identification 8 to 9
times relative to hashing, short of the pre-registered tenfold target.
\end{abstract}

\begin{IEEEkeywords}
anti-money laundering, inter-bank information sharing, leakage audit, oblivious
pseudorandom functions, pre-registration, privacy-enhancing technologies
\end{IEEEkeywords}
```

## 2. Introduction (reviewed 12 Nov)

| # | Change | Reason |
| --- | --- | --- |
| I1 | Paragraph 1: cite FATF on information sharing within data-protection rules; soften "In practice this produces many alerts…" | Motivation had no citation; the claim was uncited |
| I2 | Contribution 1: "pooled linking rule" → "cross-bank linking rule"; add that the implementation, pre-registration, amendments and sealed-test log are public | "Pooled" clashes with the pooled oracle; openness is a contribution |
| I3 | Contribution 4: add "on the fresh windows" | As A5 |

Paragraph 1:

```latex
Money laundering commonly moves funds through accounts held at different institutions.
Funds may be collected at one bank, passed through accounts at others and withdrawn
elsewhere, so the transaction monitoring of any single bank observes only some of the legs.
Alerts therefore tend to be investigated in isolation, and few cases capture a scheme as a
whole. Sharing information between banks can connect these fragments, and the Financial
Action Task Force encourages such sharing within data-protection
rules~\cite{fatf2021stocktake,fatf2022partnering}; but sharing also discloses information
about customers who may be innocent. Two questions therefore arise together: how much
detection improves with sharing, and how much a receiving bank can infer from what it is
sent.
```

Contributions 1 and 4:

```latex
\item A protocol for cross-bank detection based on minimised evidence records, OPRF
tokens~\cite{rfc9497}, a per-bank fusion stacker and a cross-bank linking rule, organised
as a ladder of sharing levels. The implementation, pre-registration, amendments and
sealed-test access log are public.
\item Case-quality measures relevant to investigators: on the fresh windows, more complete
cases and 6.8 to 8.5 times fewer alerts per linked scheme.
```

## 3. Related Work (reviewed 12 Nov)

| # | Change | Reason |
| --- | --- | --- |
| R1 | "at least two select models on the split from which they report results" → "and at least one reports peak test performance without a separate validation split~\cite{khan2024fedrd}" | **Must fix.** Only Fed-RD is documented as doing this (`related_work.md`); "two" is not supported |
| R2 | "give the strongest published transaction-level results" → "report strong transaction-level results on it, and we compare our detector with those published numbers (Table~\ref{tab:benchmark})" | "Strongest" cannot be guaranteed against work published since; the comparison is what matters |
| R3 | New paragraph on the building blocks: OPRF-based private matching, attack-based privacy risk, leakage between development and test data | Places the three methodological pieces (tokens, audit, sealed test) in their literature |

R1 sentence:

```latex
None of the studies in the table reports results on a pre-registered sealed test or
replicates them on data withheld throughout development, and at least one reports peak
test performance without a separate validation split~\cite{khan2024fedrd}.
```

R2 and R3 (replace the last paragraph of Section II):

```latex
For the data and the detector we build on AMLworld~\cite{altman2023}, a synthetic
transaction set with laundering labels and typologies. Directed multigraph
GNNs~\cite{egressy2024} and subgraph features combined with gradient
boosting~\cite{blanusa2024} report strong transaction-level results on it, and we compare
our detector with those published numbers (Table~\ref{tab:benchmark}).

Three building blocks come from other literatures. Our tokens follow the use of oblivious
pseudorandom functions for private matching and keyword search~\cite{freedman2005keyword},
in the form standardised by RFC~9497~\cite{rfc9497}. Our audit takes the attack-based view
of privacy risk, in which an adversary infers membership or attributes from what is
released~\cite{yeom2018privacy}. Our sealed test answers evidence that leakage between
development and test data inflates results in machine-learning-based
science~\cite{kapoor2023leakage}; pre-registration~\cite{nosek2018} is one remedy.
```

## 4. System (reviewed 12 Nov)

| # | Change | Reason |
| --- | --- | --- |
| S1 | Tokens, first sentence: "…without any bank holding a key that would let it tokenise arbitrary identifiers" → "…and so that no bank holds a key with which it could tokenise identifiers offline" | Banks *can* tokenise identifiers through metered online queries; that is exactly what PT2 measures |
| S2 | Define the probability bucket once: five buckets with edges 0.01, 0.05, 0.2 and 0.5 | τ ∈ {2, 3, 4} and "bucket ≥ 2" are otherwise undefined (`finmesh/schemas/evidence_v1.json`; bucket 2 ⇔ p ≥ 0.05) |
| S3 | S3 bullet: "at most 8 per account and epoch" → "with at most ε = 8 spent per account and epoch" | Ambiguous: 8 is an ε cap summed over releases (`finmesh/sharing/ldp.py`, `EPSILON_CAP`) |
| S4 | S1F bullet: add "(calibrated probability at least 0.05)" | Follows from S2 |
| S5 | Threat model: add "It learns how many queries each bank makes, but not their content." | States what the token service does see |

S1 sentence:

```latex
A bank must be able to recognise that the account a peer asks about is one of its own
counterparties, without account numbers being exchanged and so that no bank holds a key
with which it could tokenise identifiers offline.
```

S2, S3 and S4 (bullets):

```latex
\item \textbf{S2}: an evidence record containing the probability bucket (five buckets, with
edges at 0.01, 0.05, 0.2 and 0.5), the three features that deviate most from ...
\item \textbf{S3}: S2 with every field other than the time bucket and the flag released by
$k$-ary randomised response~\cite{warner1965}, at a total
$\varepsilon \in \{0.5, 1, 2, 4, 8\}$ per record, with at most $\varepsilon = 8$ spent per
account and epoch.
\item \textbf{S1F} (gated flag, introduced in Section~\ref{sec:a25}): the S1 answer, given
only when the requester's probability bucket is at least 2 (calibrated probability at least
0.05).
```

## 5. Evaluation Method (reviewed 12 Nov)

| # | Change | Reason |
| --- | --- | --- |
| E1 | **Must fix.** "Every later change was recorded as a dated amendment, with its reason, before the results it concerned existed." contradicts Section VI (A24b corrected a report page after an opening). Reword as below | Internal consistency; `docs/proposal/CHANGES.md` |
| E2 | "model settings were never tuned on validation data" → say what was fixed and what was selected (as below) | Section IV-D selects the A25 candidates on validation, so the sentence as written contradicts the next subsection; the pre-registration fixes the *registered* model settings (`preregistration.md` §6) |
| E3 | Table III note: add "H2 (a federated DP scorer, a supporting track) is reported in Section VI." | The table jumps from H1 to H3; a reviewer will ask where H2 is |
| E4 | Optional, if space allows: one sentence on compute, e.g. "All runs used a single laptop with 8 GB of memory." | Reproducibility; reviewers often ask |

E1 and E2 (replace those two sentences in IV-C):

```latex
Hypotheses (Table~\ref{tab:results}), operating points, model settings and statistical
rules were registered at the outset. Thresholds marked as provisional could be revised once,
using validation results, at a pre-planned gate (G1), after which the registration was
frozen; the registered model settings were fixed in advance rather than tuned on validation
data. Every later change was recorded as a dated amendment with its reason. All but one were
made before the results they concerned existed; the exception corrected a report page after
an opening without changing any score (Section~\ref{sec:limits}).
```

(Needs `\label{sec:limits}` on `\section{Limitations}`.)

## 6. Results (reviewed 12 Nov)

| # | Change | Reason |
| --- | --- | --- |
| X1 | **Must add.** Tokens paragraph: report that in the week-18 HI-Medium test legitimate token use exceeded the frozen budget in 2 of 16 bank-epochs (18.8% of requests), and that budgets were then sized per window from validation traffic before the fresh tests | A pre-registered (reported) outcome that the paper currently omits (`docs/eval/test/RESULTS.md`, token-budget row); the improvement plan sized the Large budgets per window |
| X2 | Robustness: "In every model the most important features are…" → "At gate G1, the payment-format shares and the self-transfer indicator were the strongest features of every baseline model; they may reflect properties of the simulator." | The source (`docs/gates/G1.md`) is about the G1 baselines; "every model" over-generalises |
| X3 | Fig. 3 caption: "with a stronger transaction-level detector that outperforms both published gradient-boosting baselines" → "with a per-bank version of the transaction-level detector of Table~\ref{tab:benchmark}" | As A2: the per-bank version is what the figure shows |
| X4 | Narratives: after "N4 met the target on both fresh tests (1.00 and 0.95)", add "although its strict grounding was lower on LI-Large (0.56) than on HI-Large (0.82)" | Balance; the numbers are already in Table VI |

X1 (add to the end of the Tokens paragraph, replacing "Legitimate token use stayed within the frozen budget on both fresh tests."):

```latex
In the week-18 HI-Medium test, legitimate use exceeded the frozen budget in 2 of 16
bank-epochs (18.8\% of token requests); for the fresh tests the budget was therefore sized
per window from validation traffic, and legitimate use stayed within it on both.
```

Checked and unchanged: data and federation, the label and metric definitions, the G1 numbers (0.508 [0.465, 0.550]; 0.864 and 0.886), the A25 selection rules and outcomes (gated flag 1.01; N4 on qwen3:8b; benchmark gap 14.5 points), the frozen-commit signature (signed by the first author, `improvement_plan_A25.md`), statistics, the audit design, and every number in Sections V-A to V-E against `RESULTS.md` and `RESULTS_LARGE.md`.

## 7. Limitations (reviewed 12 Nov)

| # | Change | Reason |
| --- | --- | --- |
| L1 | Add `\label{sec:limits}` to `\section{Limitations}` | Needed by E1 |
| L2 | Add the token limitation: the OPRF limits re-identification only as far as the per-epoch budget does (8–9-fold reduction against hashing on three of four tests; an adaptive budget made it worse) | A privacy reviewer will look for it here, not only in V-C (`audit_*.md`, `budget_replay_*`) |
| L3 | Add: with the strongest pooled model (stronger detector, LI-Large), minimised sharing recovered less than half of its gain (0.49) | The one robustness rule not met belongs among the limits (`RESULTS_LARGE.md`, H1b-L+) |
| L4 | Add: one fixed federation of eight similarly sized members; larger or unequal federations not tested | Scope of the evidence (`preregistration.md` §1, B8) |

Insert after "…but not differentially private." :

```latex
The oblivious tokens limit re-identification only as far as the per-epoch budget does:
relative to hashing, re-identification fell 8- to 9-fold on three of the four tests, short
of the tenfold target, and an adaptive budget made it worse. When the pooled model was
strongest (the stronger detector on LI-Large), minimised sharing recovered less than half of
its gain. All tests use one federation of eight members of similar size; larger or more
unequal federations were not studied.
```

## 8. Conclusion (reviewed 12 Nov)

| # | Change | Reason |
| --- | --- | --- |
| C1 | "with a competitive local detector" → "with a stronger local detector" | Matches Section V-B |
| C2 | Add one sentence on what was not met, and one on future work | A conclusion that lists only successes reads as selective; IEEE conclusions usually name next steps |

Replacement Conclusion:

```latex
Sharing a small amount of evidence about counterparty accounts, namely an alert flag and a
bucketed record addressed by metered tokens, allowed banks to link several times as many
laundering schemes as local monitoring and to recover most of the gain of a pooled model,
with far fewer alerts per linked scheme. These results held on four sealed tests, two of
which were not opened during development, without the suspected artefact features and with
a stronger local detector. Measuring leakage with attacks revealed that even the simplest
disclosure, a bare alert flag, can leak an account attribute, and a gated flag removed this
leakage on fresh data. Typology attribution and the pre-registered limit on token
re-identification were not achieved. Natural next steps are a pilot on real transaction
data under a data-sharing agreement, larger federations of unequal banks, flags with formal
privacy guarantees, and blind human review of the case narratives. We suggest that
collaborative financial-crime detection adopt the same practice of pre-registration, sealed
tests and replication on withheld data.
```

## 9. Back matter (reviewed 12 Nov)

| # | Change | Reason |
| --- | --- | --- |
| B1 | Acknowledgment: keep as is (IEEE requires the AI disclosure). Revise it only if your final use of AI assistance differs; optionally thank the department for support | IEEE author guidelines on AI-generated text |
| B2 | Data and Code Availability: replace with the merged paragraph agreed on 12 Nov (below) | Gives the repository link |
| B3 | For a double-blind venue only: replace the GitHub URL with an anonymised mirror (e.g. anonymous.4open.science) or "available on acceptance", and remove names from the author block | The URL and the author block identify the authors |

B2 (revised 12 Nov after testing the claim; see below):

```latex
\section*{Data and Code Availability}
AMLworld~\cite{altman2023} is available under the CDLA-Permissive-2.0 licence. The FinMesh
source code (MIT licence), configurations, pre-registration, amendments, sealed-test access
log and result pages are publicly available at
\url{https://github.com/allu0786ansari/FinMesh}. One command, \texttt{finmesh
paper-assets}, rebuilds Figs.~2--5 and Tables~I--VI from the committed result pages without
access to the data; the result pages themselves are reproduced from the raw AMLworld files
by the commands listed, in order, in the repository's run logs.
```

Why the earlier wording ("one command regenerates every figure and table") was changed. Tested 12 Nov in a clean clone with no data folder: `uv run finmesh paper-assets` ran in about 10 s; Tables I–VI and `assets.json` came out byte-identical to the committed files, and Figs. 2–5 pixel-identical (the PDF files differ only in their embedded creation date). But:
- Fig. 1 is drawn, not generated (TikZ source `docs/paper/static/fig_architecture.tex`);
- Table I is a curated table, copied from `docs/paper/static/`, not computed;
- the command rebuilds the paper's figures and tables **from the result pages**; producing those pages from raw data is the full pipeline (AMLworld download, then the run logs `week-01` to `week-18` and `a25`, several overnight runs on an 8 GB machine). That cannot honestly be called one command.


## 10. Final pass (after all edits)

1. Apply sections 1–9 in `main.tex`, the Table III note (E3) in `tables/tab_results.tex`, and the five new entries in `references.bib`.
2. Compile on Overleaf (pdfLaTeX; `main.tex`): check no undefined references or citations, no overfull boxes, page count, and that the reference numbers follow first citation.
3. Run `uv run finmesh paper-assets` after the section 11 code edits, then update `VERIFICATION.md` for the new statements (token-budget overrun, bucket edges, ε cap, the limitations) and rebuild `paper.docx`, `preview.pdf` and the Overleaf zip from the final source.
4. Spelling: the text uses British spelling throughout (minimised, licence, artefact); keep it consistent, or switch to American spelling if the venue asks.

## 11. Naming of the two test rounds (agreed 12 Nov)

"Week-18" is a project-schedule label, not a term a reader knows, and "A25 fresh tests" uses an internal amendment code. Use two names throughout:

- **primary tests**: the HI-Medium and LI-Medium sealed tests, which decided the pre-registered hypotheses;
- **replication tests**: the HI-Large and LI-Large windows, never opened during development, on which the later improvements were confirmed (amendment A25).

"Final amendment test" was considered and not used: to a reviewer "amendment" signals a post-hoc change, while "replication" says what these tests are for. Introduce A25 once, in the heading text of IV-D ("Replication on unopened windows"), with "(amendment A25 in the public amendment log)".

Edits (text, tables and figures):

| Where | Now | Change to |
| --- | --- | --- |
| `main.tex` IV-C, last sentence | "The week-18 tests on HI-Medium and LI-Medium decided…" | "The primary tests on HI-Medium and LI-Medium decided…" |
| `main.tex` IV-D heading | "Fresh replication (amendment A25)" | "Replication on unopened windows" + "(amendment A25 in the public amendment log)" in its first sentence |
| `main.tex` IV-D, first sentence | "after the week-18 tests … on those tests" | "after the primary tests … on those tests" |
| `main.tex` V-A | "…in the week-18 tests, and … in the fresh tests" | "…in the primary tests, and … in the replication tests" |
| `main.tex` Fig. 2 caption | "HI- and LI-Medium are the week-18 tests; HI- and LI-Large are the fresh windows, which were not opened during development." | "HI- and LI-Medium are the primary tests; HI- and LI-Large are the replication tests, on windows not opened during development." |
| `main.tex` elsewhere | "fresh tests", "fresh windows", "fresh data" (abstract, contributions, V-C, V-E, conclusion; and the plan's new text) | "replication tests" / "replication windows"; "on fresh data" may stay where it reads naturally, but use one term for the tests |
| `finmesh/paper/figures.py` (Fig. 2 panel labels) | "Week 18 tests", "A25 fresh tests" | "Primary tests", "Replication tests"; regenerate with `finmesh paper-assets` |
| `finmesh/paper/tables.py` (Table II note) | "Medium: the week-18 sealed tests; Large: the A25 fresh tests." | "Medium: the primary tests; Large: the replication tests." |
| `finmesh/paper/tables.py` (Table III note) | "Medium columns: week-18 tests; Large: A25 fresh tests." | "Medium columns: primary tests; Large: replication tests." |
| `finmesh/paper/tables.py` (Table V note) | "A25 fresh tests, seeds 0--4." | "Replication tests, seeds 0--4." |
| `finmesh/paper/tables.py` (Table VI row) | "N4 on the A25 fresh tests" | "N4 on the replication tests" |

Keep the amendment codes A24a, A24b and A25a in Limitations: they point to entries a reader can look up in the public amendment log.

## New bibliography entries (add to `references.bib`)

Each checked against its source on 12 Nov 2026.

```bibtex
@techreport{fatf2021stocktake,
  author      = {{Financial Action Task Force}},
  title       = {Stocktake on Data Pooling, Collaborative Analytics and Data Protection},
  institution = {FATF},
  address     = {Paris, France},
  month       = jul,
  year        = {2021},
  url         = {https://www.fatf-gafi.org/en/publications/Digitaltransformation/Data-pooling-collaborative-analytics-data-protection.html}
}
@techreport{fatf2022partnering,
  author      = {{Financial Action Task Force}},
  title       = {Partnering in the Fight Against Financial Crime: Data Protection,
                 Technology and Private Sector Information Sharing},
  institution = {FATF},
  address     = {Paris, France},
  month       = jul,
  year        = {2022},
  url         = {https://www.fatf-gafi.org/en/publications/Digitaltransformation/Partnering-in-the-fight-against-financial-crime.html}
}
@inproceedings{freedman2005keyword,
  author    = {Freedman, Michael J. and Ishai, Yuval and Pinkas, Benny and Reingold, Omer},
  title     = {Keyword Search and Oblivious Pseudorandom Functions},
  booktitle = {Theory of Cryptography, Second Theory of Cryptography Conference (TCC 2005)},
  series    = {Lecture Notes in Computer Science},
  volume    = {3378},
  pages     = {303--324},
  publisher = {Springer},
  year      = {2005}
}
@inproceedings{yeom2018privacy,
  author    = {Yeom, Samuel and Giacomelli, Irene and Fredrikson, Matt and Jha, Somesh},
  title     = {Privacy Risk in Machine Learning: Analyzing the Connection to Overfitting},
  booktitle = {IEEE Computer Security Foundations Symposium (CSF)},
  year      = {2018}
}
@article{kapoor2023leakage,
  author  = {Kapoor, Sayash and Narayanan, Arvind},
  title   = {Leakage and the Reproducibility Crisis in Machine-Learning-Based Science},
  journal = {Patterns},
  volume  = {4},
  number  = {9},
  pages   = {100804},
  year    = {2023},
  doi     = {10.1016/j.patter.2023.100804}
}
```

Sources: [FATF stocktake](https://www.fatf-gafi.org/en/publications/Digitaltransformation/Data-pooling-collaborative-analytics-data-protection.html); [FATF Partnering report](https://www.fatf-gafi.org/en/publications/Digitaltransformation/Partnering-in-the-fight-against-financial-crime.html) (20 July 2022, per [Norton Rose Fulbright](https://nortonrosefulbright.com/en/inside-fintech/blog/2022/07/partnering-in-the-fight-against-financial-crime-data-protection-technology-and-private-sector)); [Freedman et al., TCC 2005](https://researchr.org/publication/FreedmanIPR05/bibtex); [Yeom et al., arXiv:1709.01604, CSF 2018](https://www.arxiv.org/abs/1709.01604); [Kapoor and Narayanan, Patterns 4(9)](https://collaborate.princeton.edu/en/publications/leakage-and-the-reproducibility-crisis-in-machine-learning-based-/).

## Page budget

The paper is 8 pages, with three references on page 8. These changes add five references and about thirty lines of text; the result should still fit in 8 pages. Check after compiling.
