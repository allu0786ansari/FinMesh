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

The paper is 8 pages, with three references on page 8. These changes add five references and about eight lines of text; the result should still fit in 8 pages. Check after compiling.
