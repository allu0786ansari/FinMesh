"""Build an editable Word (.docx) version of the paper from ``main.tex``.

The LaTeX source stays the master copy. This script converts it so that co-authors can edit
in Word, or submit to a venue that asks for .docx. It needs a finished LaTeX build (section,
figure, table and citation numbers are read from its ``main.aux``), pandoc 3, python-docx
and pdftoppm.

    python docs/paper/tools/make_docx.py --aux <build>/main.aux --out docs/paper/paper.docx

Layout follows the IEEE conference template for Word: US Letter; margins 0.75 in top,
1 in bottom, 0.625 in left and right; two 3.5 in columns 0.25 in apart; Times New Roman,
10 pt body, 24 pt title, 9 pt bold abstract, 8 pt captions, tables and references. Tables
that span both columns in LaTeX (``table*``) sit in a one-column section at the point where
they are input. Running text goes through pandoc; tables are rebuilt from the ``tabular``
source; the reference list is produced by pandoc citeproc with the IEEE CSL style
(``ieee.csl``, CC BY-SA 3.0, Citation Style Language project), numbered as in the LaTeX build.
"""

from __future__ import annotations

import argparse
import copy
import re
import subprocess
import tempfile
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt
from docx.text.paragraph import Paragraph
from docx.text.run import Run

PAPER = Path(__file__).resolve().parents[1]
FONT = "Times New Roman"
ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
COLUMN_IN, PAGE_IN = 3.5, 7.0
# Word has no floats. A table that spans both columns is placed where it is input, moved
# above any figure just before it; Table I is moved to the start of Section IV, near where
# LaTeX floats it, so that Fig. 1 can follow Section III's opening text.
DEFER = {"tab_related": "IV. Evaluation Method"}
FIGURE_STYLES = ("Captioned Figure", "Figure", "Image Caption")


# ============================================================================ LaTeX helpers
def braced(s: str, i: int) -> tuple[str, int]:
    """Content of the brace group opening at s[i] == '{', and the index after it."""
    assert s[i] == "{", s[i : i + 20]
    depth = 0
    for j in range(i, len(s)):
        if j > i and s[j - 1] == "\\":
            continue
        depth += {"{": 1, "}": -1}.get(s[j], 0)
        if depth == 0:
            return s[i + 1 : j], j + 1
    raise ValueError("unbalanced braces")


def command_arg(s: str, cmd: str, start: int = 0) -> tuple[str, int]:
    i = s.index(cmd, start) + len(cmd)
    while s[i] in " \n":
        i += 1
    return braced(s, i)


def read_aux(aux: Path) -> tuple[dict[str, str], dict[str, int]]:
    text = aux.read_text()
    labels = {
        m.group(1): re.sub(r"\\mbox\s*\{(.*)\}", r"\1", m.group(2)).strip()
        for m in re.finditer(r"\\newlabel\{([^}]*)\}\{\{(.*?)\}\{\d+\}", text)
    }
    cites = {
        m.group(1): int(m.group(2)) for m in re.finditer(r"\\bibcite\{([^}]*)\}\{\{?(\d+)", text)
    }
    return labels, cites


MATH = [
    (r"\varepsilon", "\\textit{ε}"),
    (r"\tau", "\\textit{τ}"),
    (r"\pm", "±"),
    (r"\geq", "≥"),
    (r"{\ge}", "≥"),
    (r"\ge", "≥"),
    (r"\leq", "≤"),
    (r"\div", "÷"),
    (r"\in", "∈"),
    (r"\,", "\u202f"),
    ("-", "−"),
]


def math_to_text(expr: str) -> str:
    """The paper's few inline formulas, as text: Unicode symbols, italic variables."""
    out = expr
    for a, b in MATH:
        out = out.replace(a, b)
    out = re.sub(
        r"(?<![\\\w{])([a-zA-Z])(?![\w}])", r"\\textit{\1}", out
    )  # single-letter variables
    out = re.sub(r"(?<=\S)\s*([=≤≥∈])\s*", r" \1 ", out)
    return out.strip()


def common_rewrites(s: str, labels: dict[str, str], cites: dict[str, int]) -> str:
    s = re.sub(r"(?m)(?<!\\)%.*$", "", s)
    s = re.sub(r"\$([^$]+)\$", lambda m: math_to_text(m.group(1)), s)
    s = re.sub(r"\\ref\{([^}]*)\}", lambda m: labels[m.group(1)], s)
    s = re.sub(
        r"\\cite\{([^}]*)\}",
        lambda m: ", ".join(f"[{cites[k.strip()]}]" for k in m.group(1).split(",")),
        s,
    )
    s = re.sub(r"\\label\{[^}]*\}", "", s)
    return s.replace(r"\cmark", "✓").replace(r"\xmark", "✗").replace("{,}", ",")


# ============================================================================ front matter
def front_matter(tex: str) -> dict:
    title, _ = command_arg(tex, r"\title")
    title = re.sub(r"\\\\\s*", " ", title).strip()
    author_src, _ = command_arg(tex, r"\author")
    authors = []
    for block in author_src.split(r"\and"):
        name, _ = command_arg(block, r"\IEEEauthorblockN")
        aff, _ = command_arg(block, r"\IEEEauthorblockA")
        lines = []
        for line in re.split(r"\\\\", aff):
            line = line.strip()
            m = re.fullmatch(r"\\textit\{(.*)\}", line)
            if line:
                lines.append((m.group(1) if m else line, bool(m)))
        authors.append({"name": name.strip(), "lines": lines})
    abstract = tex[tex.index(r"\begin{abstract}") + 16 : tex.index(r"\end{abstract}")]
    keywords = tex[tex.index(r"\begin{IEEEkeywords}") + 20 : tex.index(r"\end{IEEEkeywords}")]
    return {"title": title, "authors": authors, "abstract": abstract, "keywords": keywords}


# ============================================================================ body for pandoc
def body_latex(tex: str, labels: dict[str, str], cites: dict[str, int]) -> str:
    body = tex[tex.index(r"\section{Introduction}") : tex.index(r"\bibliographystyle")]
    body = re.sub(r"(?m)(?<!\\)%.*$", "", body)
    body = re.sub(r"\\input\{tables/(\w+)\.tex\}", r"\n\n@@TABLE:\1@@\n\n", body)

    def figure(m: re.Match) -> str:
        content = m.group(1)
        num = labels[re.search(r"\\label\{([^}]*)\}", content).group(1)]
        cap, _ = command_arg(content, r"\caption")
        img = re.search(r"\\includegraphics(?:\[[^\]]*\])?\{(fig_\w+)\}", content).group(1)
        return (
            f"\n\n\\begin{{figure}}\n\\includegraphics{{{img}.png}}\n"
            f"\\caption{{Fig.~{num}. {cap}}}\n\\end{{figure}}\n\n"
        )

    body = re.sub(r"\\begin\{figure\}(?:\[[^\]]*\])?(.*?)\\end\{figure\}", figure, body, flags=re.S)
    body = common_rewrites(body, labels, cites)
    sec = sub = 0

    def heading(m: re.Match) -> str:
        nonlocal sec, sub
        level, star, text = m.group(1), m.group(2), m.group(3)
        if star:
            return rf"\section*{{{text}}}"
        if level == "section":
            sec, sub = sec + 1, 0
            return rf"\section*{{{ROMAN[sec - 1]}. {text}}}"
        sub += 1
        return rf"\subsection*{{{chr(64 + sub)}. {text}}}"

    body = re.sub(r"\\(section|subsection)(\*?)\{([^}]*)\}", heading, body)
    return (
        "\\documentclass{article}\n\\begin{document}\n"
        + body
        + "\n\\section*{References}\n\n@@REFERENCES@@\n\n\\end{document}\n"
    )


# ============================================================================ tables
def parse_inline(s: str, fmt: frozenset = frozenset()) -> list[tuple[str, frozenset]]:
    """LaTeX text -> [(text, {'b', 'i', 'tt'})]."""
    out: list[tuple[str, frozenset]] = []
    i, buf = 0, []

    def flush():
        if buf:
            out.append(("".join(buf), fmt))
            buf.clear()

    cmds = {r"\textbf": "b", r"\emph": "i", r"\textit": "i", r"\texttt": "tt"}
    s = re.sub(r"\s+", " ", s)
    while i < len(s):
        hit = next((c for c in cmds if s.startswith(c + "{", i)), None)
        if hit:
            flush()
            inner, i = braced(s, i + len(hit))
            out += parse_inline(inner, fmt | {cmds[hit]})
            continue
        if s[i] == "{":
            flush()
            inner, i = braced(s, i)
            out += parse_inline(inner, fmt)
            continue
        for a, b in (
            (r"\%", "%"),
            (r"\&", "&"),
            (r"\ ", " "),
            ("---", "—"),
            ("--", "–"),
            ("~", "\u00a0"),
            (r"\_", "_"),
            (r"\{", "{"),
            (r"\}", "}"),
            ("\\quad ", "\u2003"),
            ("\\quad", "\u2003"),
        ):
            if s.startswith(a, i):
                buf.append(b)
                i += len(a)
                break
        else:
            buf.append(s[i])
            i += 1
    flush()
    return [(t, f) for t, f in out if t]


def parse_table(src: str) -> dict:
    wide = r"\begin{table*}" in src
    caption, _ = command_arg(src, r"\caption")
    note = None
    if r"\parbox{\linewidth}" in src:
        k = src.index(r"\parbox{\linewidth}") + len(r"\parbox{\linewidth}")
        note, _ = braced(src, k)
        note = re.sub(r"^\\scriptsize\s*", "", note.strip())
    i = src.index(r"\begin{tabular}") + len(r"\begin{tabular}")
    spec, j = braced(src, i)
    body = src[j : src.index(r"\end{tabular}")]
    m = re.fullmatch(r"\*\{(\d+)\}\{.*\}", spec)
    aligns = (
        ["p"] * int(m.group(1)) if m else [c for c in re.sub(r"\{[^}]*\}", "", spec) if c in "lcrp"]
    )
    rows, rule_next = [], False
    for chunk in re.split(r"\\\\", body):
        chunk = chunk.strip()
        while chunk.startswith(r"\hline"):
            rule_next = True
            chunk = chunk[len(r"\hline") :].strip()
        if not chunk:
            continue
        cells = []
        for raw in re.split(r"(?<!\\)&", chunk):
            raw = raw.strip()
            mc = re.match(r"\\multicolumn\{(\d+)\}\{(\w)\}", raw)
            if mc:
                content, _ = braced(raw, mc.end())
                cells.append({"span": int(mc.group(1)), "align": mc.group(2), "text": content})
            else:
                cells.append({"span": 1, "align": None, "text": raw})
        rows.append({"cells": cells, "rule_above": rule_next})
        rule_next = False
    return {"wide": wide, "caption": caption, "note": note, "aligns": aligns, "rows": rows}


ALIGN = {
    "l": WD_ALIGN_PARAGRAPH.LEFT,
    "c": WD_ALIGN_PARAGRAPH.CENTER,
    "r": WD_ALIGN_PARAGRAPH.RIGHT,
    "p": WD_ALIGN_PARAGRAPH.LEFT,
}


def add_runs(par, pieces, size, base_italic=False):
    for text, f in pieces:
        r = par.add_run(text)
        set_font(
            r,
            size=size,
            bold=True if "b" in f else None,
            italic=True if ("i" in f or base_italic) else None,
        )
        if "tt" in f:
            rf = r._element.get_or_add_rPr().get_or_add_rFonts()
            for a in ("w:ascii", "w:hAnsi", "w:cs"):
                rf.set(qn(a), "Courier New")


def set_borders(parent, tag: str, edges: dict[str, int]):
    b = OxmlElement(tag)
    names = ("top", "left", "bottom", "right") + (
        ("insideH", "insideV") if tag == "w:tblBorders" else ()
    )
    for edge in names:
        e = OxmlElement(f"w:{edge}")
        size = edges.get(edge, 0)
        e.set(qn("w:val"), "single" if size else "nil")
        if size:
            e.set(qn("w:sz"), str(size))
            e.set(qn("w:space"), "0")
            e.set(qn("w:color"), "000000")
        b.append(e)
    old = parent.find(qn(tag))
    if old is not None:
        parent.remove(old)
    insert_ordered(parent, b, AFTER_TBLBORDERS if tag == "w:tblBorders" else AFTER_TCBORDERS)


# schema order: an element must precede these siblings
AFTER_TBLBORDERS = (
    "w:shd",
    "w:tblLayout",
    "w:tblCellMar",
    "w:tblLook",
    "w:tblCaption",
    "w:tblDescription",
    "w:tblPrChange",
)
AFTER_TBLLAYOUT = AFTER_TBLBORDERS[2:]
AFTER_TCBORDERS = (
    "w:shd",
    "w:noWrap",
    "w:tcMar",
    "w:textDirection",
    "w:tcFitText",
    "w:vAlign",
    "w:hideMark",
    "w:headers",
    "w:cellIns",
    "w:cellDel",
    "w:cellMerge",
    "w:tcPrChange",
)
AFTER_TCMAR = AFTER_TCBORDERS[3:]


def insert_ordered(parent, el, successors):
    for child in parent:
        if child.tag in {qn(t) for t in successors}:
            child.addprevious(el)
            return
    parent.append(el)


def plain_table(doc, rows: int, cols: int):
    tbl = doc.add_table(rows=rows, cols=cols)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tpr = tbl._tbl.tblPr
    st = tpr.find(qn("w:tblStyle"))
    if st is not None:
        tpr.remove(st)
    set_borders(tpr, "w:tblBorders", {})
    return tbl


def build_table(doc, t: dict, labels, cites):
    ncol = len(t["aligns"])
    for row in t["rows"]:
        for c in row["cells"]:
            c["pieces"] = parse_inline(common_rewrites(c["text"], labels, cites))
    avail = PAGE_IN if t["wide"] else COLUMN_IN
    if all(a == "p" for a in t["aligns"]):
        widths = [avail / ncol] * ncol
    else:  # preferred widths from content length, scaled down to the space available
        need = [0.2] * ncol
        for row in t["rows"]:
            col = 0
            for c in row["cells"]:
                if c["span"] == 1:
                    need[col] = max(need[col], 0.056 * sum(len(x) for x, _ in c["pieces"]) + 0.1)
                col += c["span"]
        widths = [w * min(1.0, avail / sum(need)) for w in need]
    tbl = plain_table(doc, len(t["rows"]), ncol)
    ruled = [k for k, row in enumerate(t["rows"]) if row["rule_above"]]
    header_rows = ruled[1] if len(ruled) > 1 and ruled[0] == 0 else 0
    lay = OxmlElement("w:tblLayout")
    lay.set(qn("w:type"), "fixed")
    insert_ordered(tbl._tbl.tblPr, lay, AFTER_TBLLAYOUT)
    for k, w in enumerate(widths):
        tbl.columns[k].width = Inches(w)
    for r_i, row in enumerate(t["rows"]):
        for k in range(ncol):
            cell = tbl.cell(r_i, k)
            cell.width = Inches(widths[k])
            edges = {}
            if row["rule_above"]:
                edges["top"] = 6
            if r_i == len(t["rows"]) - 1:
                edges["bottom"] = 6
            tcpr = cell._tc.get_or_add_tcPr()
            set_borders(tcpr, "w:tcBorders", edges)
            mar = OxmlElement("w:tcMar")
            for edge, v in (("left", 45), ("right", 45)):
                e = OxmlElement(f"w:{edge}")
                e.set(qn("w:w"), str(v))
                e.set(qn("w:type"), "dxa")
                mar.append(e)
            insert_ordered(tcpr, mar, AFTER_TCMAR)
        col = 0
        for c in row["cells"]:
            cell = tbl.cell(r_i, col)
            if c["span"] > 1:
                cell = cell.merge(tbl.cell(r_i, col + c["span"] - 1))
            p = cell.paragraphs[0]
            para_format(
                p, align=ALIGN[c["align"] or t["aligns"][col]], before=1, after=1, first=Inches(0)
            )
            add_runs(p, c["pieces"], 8)
            col += c["span"]
        trpr = tbl.rows[r_i]._tr.get_or_add_trPr()
        trpr.append(OxmlElement("w:cantSplit"))
        if header_rows and r_i < header_rows:  # repeated on a new page if the table breaks
            trpr.append(OxmlElement("w:tblHeader"))
    return tbl


# ============================================================================ Word helpers
def set_font(run, size=None, bold=None, italic=None, small_caps=None):
    rpr = run._element.get_or_add_rPr()
    rf = rpr.get_or_add_rFonts()
    for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        if rf.get(qn(a)) != "Courier New":
            rf.set(qn(a), FONT)
    if size is not None:
        run.font.size = Pt(size)
        szcs = rpr.find(qn("w:szCs"))
        if szcs is None:
            szcs = OxmlElement("w:szCs")
            rpr.append(szcs)
        szcs.set(qn("w:val"), str(int(size * 2)))
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if small_caps is not None:
        run.font.small_caps = small_caps


def style_runs(par, **kw):
    for r in par._p.iter(qn("w:r")):
        set_font(Run(r, par), **kw)


def para_format(
    par, align=None, before=0, after=0, first=None, left=None, hanging=None, keep_next=None
):
    pf = par.paragraph_format
    if align is not None:
        pf.alignment = align
    pf.space_before, pf.space_after = Pt(before), Pt(after)
    pf.line_spacing = 1.0
    if left is not None:
        pf.left_indent = left
    if first is not None:
        pf.first_line_indent = first
    if hanging is not None:
        pf.first_line_indent = -hanging
    if keep_next is not None:
        pf.keep_with_next = keep_next


def get_style(doc, name):
    for s in doc.styles:
        if s.name == name:
            return s
    return None


def define_styles(doc):
    for el in doc.styles.element.iter(qn("w:rFonts")):
        for a in list(el.attrib):
            del el.attrib[a]
        for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
            el.set(qn(a), FONT)
    for el in list(doc.styles.element.iter(qn("w:color"))):
        el.getparent().remove(el)
    for name in ("Normal", "Body Text", "First Paragraph", "Compact"):
        s = get_style(doc, name)
        if s is None:
            continue
        s.font.size = Pt(10)
        pf = s.paragraph_format
        pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        pf.space_before = pf.space_after = Pt(0)
        pf.line_spacing = 1.0
        if name in ("Body Text", "First Paragraph"):
            pf.first_line_indent = Inches(0.2)
    for name in ("Heading 1", "Heading 2"):
        s = get_style(doc, name)
        s.font.size, s.font.bold = Pt(10), False
        pf = s.paragraph_format
        pf.keep_with_next, pf.line_spacing = True, 1.0
        if name == "Heading 1":
            s.font.small_caps, s.font.italic = True, False
            pf.alignment, pf.space_before, pf.space_after = WD_ALIGN_PARAGRAPH.CENTER, Pt(8), Pt(4)
        else:
            s.font.italic, s.font.small_caps = True, False
            pf.alignment, pf.space_before, pf.space_after = WD_ALIGN_PARAGRAPH.LEFT, Pt(6), Pt(3)


def sectpr(num: int):
    sp = OxmlElement("w:sectPr")
    t = OxmlElement("w:type")
    t.set(qn("w:val"), "continuous")
    sp.append(t)
    pg = OxmlElement("w:pgSz")
    pg.set(qn("w:w"), "12240")
    pg.set(qn("w:h"), "15840")
    sp.append(pg)
    mar = OxmlElement("w:pgMar")
    for k, v in {
        "top": 1080,
        "right": 900,
        "bottom": 1440,
        "left": 900,
        "header": 720,
        "footer": 720,
        "gutter": 0,
    }.items():
        mar.set(qn(f"w:{k}"), str(v))
    sp.append(mar)
    c = OxmlElement("w:cols")
    c.set(qn("w:num"), str(num))
    c.set(qn("w:space"), "360")
    sp.append(c)
    return sp


def section_break(doc, before_el, cols_of_ending_section: int):
    """A tiny empty paragraph before ``before_el`` that ends a section with that many columns."""
    p = doc.add_paragraph()
    before_el.addprevious(p._p)
    para_format(p, first=Inches(0))
    ppr = p._p.get_or_add_pPr()
    rpr = OxmlElement("w:rPr")
    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), "2")
    rpr.append(sz)
    ppr.append(rpr)
    ppr.append(sectpr(cols_of_ending_section))
    return p


def new_par(doc, before_el, **fmt):
    p = doc.add_paragraph()
    before_el.addprevious(p._p)
    para_format(p, **fmt)
    return p


# ============================================================================ build
def build(aux: Path, out: Path, csl: Path) -> None:
    tex = (PAPER / "main.tex").read_text()
    labels, cites = read_aux(aux)
    fm = front_matter(tex)
    with tempfile.TemporaryDirectory() as tmpd:
        tmp = Path(tmpd)
        for pdf in (PAPER / "figures").glob("fig_*.pdf"):
            subprocess.run(
                ["pdftoppm", "-r", "600", "-png", "-singlefile", str(pdf), str(tmp / pdf.stem)],
                check=True,
            )
        (tmp / "body.tex").write_text(body_latex(tex, labels, cites))
        fm_tex = common_rewrites(fm["abstract"], labels, cites) + "\n\n@@KW@@ " + fm["keywords"]
        (tmp / "fm.tex").write_text(
            "\\documentclass{article}\\begin{document}\n" + fm_tex + "\n\\end{document}\n"
        )
        order = sorted(cites, key=cites.get)
        (tmp / "refs.md").write_text(" ".join(f"[@{k}]" for k in order) + "\n")

        def run(*a):
            subprocess.run(list(a), cwd=tmp, check=True)

        run(
            "pandoc",
            "body.tex",
            "-f",
            "latex",
            "-t",
            "docx",
            "--resource-path",
            str(tmp),
            "-o",
            "body.docx",
        )
        run("pandoc", "fm.tex", "-f", "latex", "-t", "docx", "-o", "fm.docx")
        run(
            "pandoc",
            "refs.md",
            "--citeproc",
            "--csl",
            str(csl),
            "--bibliography",
            str(PAPER / "references.bib"),
            "-t",
            "docx",
            "-o",
            "refs.docx",
        )
        doc = Document(str(tmp / "body.docx"))
        fmdoc = Document(str(tmp / "fm.docx"))
        refdoc = Document(str(tmp / "refs.docx"))
    define_styles(doc)
    body = doc.element.body
    first = body[0]

    # ---- title and authors: one column
    t = new_par(doc, first, align=WD_ALIGN_PARAGRAPH.CENTER, after=10)
    set_font(t.add_run(fm["title"]), size=24)
    n = len(fm["authors"])
    atab = plain_table(doc, 1, n)
    first.addprevious(atab._tbl)
    for cell, a in zip(atab.rows[0].cells, fm["authors"], strict=False):
        cell.width = Inches(PAGE_IN / n)
        p = cell.paragraphs[0]
        para_format(p, align=WD_ALIGN_PARAGRAPH.CENTER, after=1)
        set_font(p.add_run(a["name"]), size=11)
        for text, ital in a["lines"]:
            q = cell.add_paragraph()
            para_format(q, align=WD_ALIGN_PARAGRAPH.CENTER)
            add_runs(q, parse_inline(text), 10, base_italic=ital)
    section_break(doc, first, 1)

    # ---- abstract and index terms: start of the two-column part
    abstract_p, keywords_p = [p for p in fmdoc.paragraphs if p.text.strip()][:2]
    for src, lead_text, after in ((abstract_p, "Abstract—", 3), (keywords_p, "Index Terms—", 6)):
        el = copy.deepcopy(src._p)
        first.addprevious(el)
        par = Paragraph(el, doc._body)
        for r in par.runs:
            if "@@KW@@" in r.text:
                r.text = r.text.replace("@@KW@@", "").lstrip()
        lead = OxmlElement("w:r")
        par.runs[0]._r.addprevious(lead)
        Run(lead, par).text = lead_text
        style_runs(par, size=9, bold=True)
        set_font(par.runs[0], size=9, bold=True, italic=True)
        par.style = get_style(doc, "Normal")
        para_format(par, align=WD_ALIGN_PARAGRAPH.JUSTIFY, after=after, first=Inches(0.2))

    # ---- walk the body: tables, figures, captions, references
    for el in list(body):
        if el.tag != qn("w:p"):
            continue
        par = Paragraph(el, doc._body)
        txt, style = par.text.strip(), (par.style.name if par.style is not None else "")
        m = re.fullmatch(r"@@TABLE:(\w+)@@", txt)
        if m:
            src = (PAPER / "tables" / f"{m.group(1)}.tex").read_text()
            t = parse_table(src)
            num = labels[re.search(r"\\label\{([^}]*)\}", src).group(1)]
            anchor = el
            if t["wide"]:
                if m.group(1) in DEFER:
                    anchor = next(
                        h
                        for h in body.iter(qn("w:p"))
                        if Paragraph(h, doc._body).text.strip() == DEFER[m.group(1)]
                    )
                while True:
                    prev = anchor.getprevious()
                    pp = (
                        Paragraph(prev, doc._body)
                        if prev is not None and prev.tag == qn("w:p")
                        else None
                    )
                    if pp is None or (pp._p.pPr is not None and pp._p.pPr.sectPr is not None):
                        break
                    if (pp.style is not None and pp.style.name in FIGURE_STYLES) or (
                        not pp.text.strip() and pp._p.find(".//" + qn("w:drawing")) is not None
                    ):
                        anchor = prev
                        continue
                    break
                section_break(doc, anchor, 2)
            el_marker, el = el, anchor
            cap = new_par(
                doc,
                el,
                align=WD_ALIGN_PARAGRAPH.CENTER,
                before=6,
                after=3,
                first=Inches(0),
                keep_next=True,
            )
            r1 = cap.add_run(f"TABLE {num}")
            set_font(r1, size=8)
            r1.add_break(WD_BREAK.LINE)
            add_runs(cap, parse_inline(common_rewrites(t["caption"], labels, cites)), 8)
            for r in cap.runs[1:]:
                r.font.small_caps = True
            el.addprevious(build_table(doc, t, labels, cites)._tbl)
            if t["note"]:
                note = new_par(
                    doc, el, align=WD_ALIGN_PARAGRAPH.JUSTIFY, before=2, after=8, first=Inches(0)
                )
                add_runs(note, parse_inline(common_rewrites(t["note"], labels, cites)), 7)
            else:
                new_par(doc, el, after=6, first=Inches(0))
            if t["wide"]:
                section_break(doc, el, 1)
            body.remove(el_marker)
            continue
        if txt == "@@REFERENCES@@":
            for rp in refdoc.paragraphs:
                if rp.style is None or rp.style.name != "Bibliography":
                    continue
                new = copy.deepcopy(rp._p)
                for h in list(new.iter(qn("w:hyperlink"))):  # its link targets live in refs.docx
                    for child in list(h):
                        h.addprevious(child)
                    h.getparent().remove(h)
                el.addprevious(new)
                np_ = Paragraph(new, doc._body)
                np_.style = get_style(doc, "Normal")
                style_runs(np_, size=8)
                para_format(
                    np_,
                    align=WD_ALIGN_PARAGRAPH.JUSTIFY,
                    after=1,
                    left=Inches(0.3),
                    hanging=Inches(0.3),
                )
            body.remove(el)
            continue
        if style == "Image Caption":
            style_runs(par, size=8)
            para_format(par, align=WD_ALIGN_PARAGRAPH.JUSTIFY, before=3, after=8, first=Inches(0))
        elif style in ("Captioned Figure", "Figure"):
            para_format(
                par,
                align=WD_ALIGN_PARAGRAPH.CENTER,
                before=6,
                after=2,
                first=Inches(0),
                keep_next=True,
            )
        elif style in ("Body Text", "First Paragraph", "Compact"):
            style_runs(par, size=10)

    final = doc.sections[-1]._sectPr
    final.getparent().replace(final, sectpr(2))
    doc.core_properties.title = fm["title"]
    doc.core_properties.author = "; ".join(a["name"] for a in fm["authors"])
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out))


ORDER = {
    "style": (
        "name aliases basedOn next link autoRedefine hidden uiPriority semiHidden "
        "unhideWhenUsed qFormat locked personal personalCompose personalReply rsid "
        "pPr rPr tblPr trPr tcPr tblStylePr"
    ),
    "pPr": (
        "pStyle keepNext keepLines pageBreakBefore framePr widowControl numPr "
        "suppressLineNumbers pBdr shd tabs suppressAutoHyphens kinsoku wordWrap "
        "overflowPunct topLinePunct autoSpaceDE autoSpaceDN bidi adjustRightInd snapToGrid "
        "spacing ind contextualSpacing mirrorIndents suppressOverlap jc textDirection "
        "textAlignment textboxTightWrap outlineLvl divId cnfStyle rPr sectPr pPrChange"
    ),
    "settings": (
        "writeProtection view zoom removePersonalInformation embedTrueTypeFonts "
        "embedSystemFonts saveSubsetFonts hideSpellingErrors hideGrammaticalErrors proofState "
        "stylePaneFormatFilter trackRevisions doNotTrackMoves defaultTabStop "
        "drawingGridHorizontalSpacing drawingGridVerticalSpacing "
        "displayHorizontalDrawingGridEvery displayVerticalDrawingGridEvery "
        "characterSpacingControl savePreviewPicture footnotePr endnotePr compat docVars rsids "
        "mathPr themeFontLang clrSchemeMapping decimalSymbol listSeparator"
    ),
    "tcPr": (
        "cnfStyle tcW gridSpan hMerge vMerge tcBorders shd noWrap tcMar textDirection "
        "tcFitText vAlign hideMark headers cellIns cellDel cellMerge tcPrChange"
    ),
}


def tidy_package(path: Path) -> None:
    """Put pandoc's default parts into schema order, so that strict readers accept the file."""
    import zipfile

    from lxml import etree

    w = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    rank = {tag: {n: i for i, n in enumerate(order.split())} for tag, order in ORDER.items()}
    with zipfile.ZipFile(path) as z:
        parts = {n: z.read(n) for n in z.namelist() if not n.endswith("/")}
    for name in ("word/styles.xml", "word/document.xml", "word/settings.xml", "word/numbering.xml"):
        if name not in parts:
            continue
        root = etree.fromstring(parts[name])
        for tag, r in rank.items():
            for el in root.iter(w + tag):
                kids = [k for k in el if isinstance(k.tag, str)]
                if all(etree.QName(k).localname in r for k in kids):
                    kids.sort(key=lambda k: r[etree.QName(k).localname])
                    for k in kids:
                        el.append(k)
        for z_el in list(root.iter(w + "zoom")):
            z_el.getparent().remove(z_el)
        for ns in root.iter(w + "nsid"):
            ns.set(w + "val", ns.get(w + "val").rjust(8, "0"))
        parts[name] = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for n, data in parts.items():
            z.writestr(n, data)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--aux", type=Path, required=True, help="main.aux of a finished LaTeX build")
    ap.add_argument("--out", type=Path, default=PAPER / "paper.docx")
    ap.add_argument("--csl", type=Path, default=Path(__file__).with_name("ieee.csl"))
    a = ap.parse_args()
    build(a.aux, a.out, a.csl)
    tidy_package(a.out)
    print(a.out)


if __name__ == "__main__":
    main()
