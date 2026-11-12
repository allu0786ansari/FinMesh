# Paper (IEEE format)

| Path | What it is |
| --- | --- |
| `main.tex` | The full draft (IEEEtran conference, 8 pages with references): every section written, every number taken from the result pages; for the authors to edit |
| `figures/fig_*.pdf` | Vector figures (PNG previews alongside) |
| `tables/tab_*.tex` | IEEEtran table floats, `\input` by `main.tex` |
| `static/fig_architecture.tex` | Fig. 1, the protocol diagram (TikZ source of `figures/fig_architecture.pdf`; drawn, not generated) |
| `static/tab_related.tex` | The related-work comparison (curated; sources in `related_work.md`) |
| `references.bib` | Every entry checked against its primary source |
| `related_work.md` | Draft related-work text and the source of every table entry |
| `VERIFICATION.md` | Every factual statement in the draft mapped to the result page or code it comes from |
| `assets.json` | Every number a figure or table shows, for checking against the result pages |
| `paper.docx` | Editable Word version of the draft in IEEE two-column layout (generated from `main.tex`; see below) |
| `tools/make_docx.py`, `tools/ieee.csl` | The Word converter and the IEEE citation style it uses (CC BY-SA 3.0, Citation Style Language project) |
| `preview.pdf` | A compiled preview of the draft (local build; see below) |

## Regenerate

```bash
uv run finmesh paper-assets
```

The command rebuilds `figures/`, `tables/` and `assets.json` from the committed result pages:
- `docs/eval/test` and `docs/eval/a25`;
- `docs/gates` and `docs/data_profile`.

It needs no data folder. Fig. 1 is drawn rather than generated; rebuild it with `cd static && pdflatex fig_architecture && mv fig_architecture.pdf ../figures/`. A value missing from a page stops the build rather than being guessed.

## IEEE conventions applied

**Figures:**
- Sized to one column, exactly 3.5 in wide, so text prints at its set size.
- Times-compatible serif at 8 pt (7 pt ticks), 0.5 pt axes.
- Fonts embedded as TrueType, with no Type 3 fonts (what IEEE PDF eXpress checks).
- Vector PDF.
- Captions below the figure, as "Fig. N."

**Tables:**
- Captions above the table; IEEEtran numbers them in Roman numerals.
- `\hline` rules, footnote-size text, notes in script size under the table.
- Wide tables use `table*`.

**Colour:**
- The sharing levels use one blue ramp, light to dark. It is validated as an ordinal ramp on white and stays legible in greyscale print, and S0 and S2 keep the same colour in every figure.
- Dataset and track distinctions add marker shapes, so no figure relies on colour alone.

**Bibliography:** `cite` with the standard `IEEEtran.bst`.

## Build the PDF

Use your venue's official IEEE template (the Overleaf "IEEE Conference Template" ships IEEEtran.cls V1.8b and IEEEtran.bst). Upload `main.tex`, `references.bib`, `figures/` and `tables/`, then build:

```bash
pdflatex main && bibtex main && pdflatex main && pdflatex main
```

`preview.pdf` was built in the cloud workspace with IEEEtran.cls V1.8 and the natbib variant of the IEEE bibliography style. Your official build will differ only in small typographic details.

## Word version

`paper.docx` is generated from `main.tex`, so `main.tex` stays the master copy. Rebuild it after a LaTeX build, which supplies the section, figure, table and citation numbers:

```bash
python docs/paper/tools/make_docx.py --aux <build folder>/main.aux --out docs/paper/paper.docx
```

It needs pandoc 3, python-docx and pdftoppm. It uses the IEEE Word template's page set-up: US Letter, two 3.5 in columns and Times New Roman 10 pt. Word has no floating figures, so tables that span both columns sit in a one-column block near where they are cited, and figures stay where they are in the text. Move them by hand if a page breaks badly.
