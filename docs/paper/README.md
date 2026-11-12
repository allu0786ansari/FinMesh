# Paper (IEEE format)

| Path | What it is |
| --- | --- |
| `main.tex` | The full draft (IEEEtran conference, 8 pages with references; revised 12 Nov, see `REVISION_PLAN.md`): every section written, every number taken from the result pages; for the authors to edit |
| `figures/fig_*.pdf` | Vector figures (PNG previews alongside) |
| `tables/tab_*.tex` | IEEEtran table floats, `\input` by `main.tex` |
| `static/fig_architecture.tex` | Fig. 1, the protocol diagram (TikZ source of `figures/fig_architecture.pdf`; drawn, not generated) |
| `static/tab_related.tex` | The related-work comparison (curated; sources in `related_work.md`) |
| `references.bib` | Every entry checked against its primary source |
| `related_work.md` | Draft related-work text and the source of every table entry |
| `VERIFICATION.md` | Every factual statement in the draft mapped to the result page or code it comes from |
| `assets.json` | Every number a figure or table shows, for checking against the result pages |
| `paper.docx` | Editable Word version of the draft in IEEE two-column layout (generated from `main.tex`; see below) |
| `tools/make_overleaf.sh` | Packs the paper as an Overleaf project (.zip); see below |
| `tools/make_docx.py`, `tools/ieee.csl` | The Word converter and the IEEE citation style it uses (CC BY-SA 3.0, Citation Style Language project) |
| `REVISION_PLAN.md` | The section-by-section review of 12 Nov and what was changed |
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

`preview.pdf` is built with IEEEtran.cls V1.8b and the standard IEEEtran.bst, as on Overleaf.

## Word version

`paper.docx` is generated from `main.tex`, so `main.tex` stays the master copy. Rebuild it after a LaTeX build, which supplies the section, figure, table and citation numbers:

```bash
python docs/paper/tools/make_docx.py --aux <build folder>/main.aux --out docs/paper/paper.docx
```

It needs pandoc 3, python-docx and pdftoppm. It uses the IEEE Word template's page set-up: US Letter, two 3.5 in columns and Times New Roman 10 pt. Word has no floating figures, so tables that span both columns sit in a one-column block near where they are cited, and figures stay where they are in the text. Move them by hand if a page breaks badly.

## Overleaf

```bash
bash docs/paper/tools/make_overleaf.sh            # writes docs/paper/FinMesh_paper_overleaf.zip
```

The .zip has `main.tex` at the top, `references.bib`, `figures/*.pdf`, `tables/*.tex`, the TikZ source of Fig. 1 under `source/` and a short README. On Overleaf, choose New Project, then Upload Project, and set the compiler to pdfLaTeX with `main.tex` as the main document. Overleaf provides `IEEEtran.cls` and `IEEEtran.bst`. The package was test-built with IEEEtran.cls V1.8b and the standard IEEEtran.bst: 8 pages, no errors or warnings, all fonts embedded. Once you edit on Overleaf, Overleaf is the master copy; copy changes back here if the repository should follow.
