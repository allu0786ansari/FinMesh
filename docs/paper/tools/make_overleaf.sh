#!/usr/bin/env bash
# Pack the paper as an Overleaf project: main.tex at the top, the vector figures, the tables,
# the bibliography and the TikZ source of Fig. 1. Overleaf supplies IEEEtran.cls and
# IEEEtran.bst. Usage: bash docs/paper/tools/make_overleaf.sh [out.zip]
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
out="$(realpath -m "${1:-$here/FinMesh_paper_overleaf.zip}")"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/figures" "$tmp/tables" "$tmp/source"
cp "$here/main.tex" "$here/references.bib" "$tmp/"
cp "$here"/figures/fig_*.pdf "$tmp/figures/"
cp "$here"/tables/tab_*.tex "$tmp/tables/"
cp "$here/static/fig_architecture.tex" "$tmp/source/"
cat > "$tmp/README.txt" <<'TXT'
FinMesh paper: Overleaf project

Upload: Overleaf > New Project > Upload Project > choose this .zip.
Settings (Menu): Compiler = pdfLaTeX, Main document = main.tex, TeX Live = latest.
Overleaf provides IEEEtran.cls and IEEEtran.bst, so nothing else is needed.

Files
  main.tex            the paper (title, authors, all sections)
  references.bib      bibliography (every entry checked against its source)
  figures/*.pdf       vector figures (Fig. 1 to Fig. 5)
  tables/*.tex        Tables I to VI, \input by main.tex; edit them here directly
  source/fig_architecture.tex
                      TikZ source of Fig. 1. To change Fig. 1, open this file,
                      set it as the main document, compile, download the PDF and
                      replace figures/fig_architecture.pdf; then set main.tex back
                      as the main document.

If your venue gives its own IEEE template, keep its IEEEtran.cls and copy in the
text of main.tex from \begin{document} onwards.
TXT
rm -f "$out"
(cd "$tmp" && zip -qrX "$out" .)
echo "$out"
