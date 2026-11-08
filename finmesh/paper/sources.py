"""Read the paper's numbers from the committed result pages (no data folder needed).

Every figure and table of the paper is built from pages already in the repository:
the sealed-test pages (``docs/eval/test``), the A25 pages (``docs/eval/a25``), the G0
evidence (``docs/gates``) and the data profiles (``docs/data_profile``). A value that a
page does not carry raises :class:`MissingValue` instead of being guessed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from finmesh.paths import REPO_ROOT

DOCS = REPO_ROOT / "docs"
MEDIUM: tuple[str, ...] = ("HI-Medium", "LI-Medium")
LARGE: tuple[str, ...] = ("HI-Large-W16", "LI-Large-W16")
DATASETS: tuple[str, ...] = (*MEDIUM, *LARGE)
LABEL = {
    "HI-Medium": "HI-Medium",
    "LI-Medium": "LI-Medium",
    "HI-Large-W16": "HI-Large",
    "LI-Large-W16": "LI-Large",
}

_NUM = r"-?[0-9][0-9,]*(?:\.[0-9]+)?"
_CI = re.compile(rf"({_NUM})\s*\[({_NUM}),\s*({_NUM})\]")


class MissingValue(LookupError):
    """A page does not carry a value the paper needs."""


@dataclass(frozen=True)
class CI:
    est: float
    lo: float | None = None
    hi: float | None = None

    @classmethod
    def parse(cls, text: str) -> CI:
        m = _CI.search(text)
        if m:
            return cls(*(_f(g) for g in m.groups()))
        n = re.search(_NUM, text)
        if not n:
            raise MissingValue(f"no number in {text!r}")
        return cls(_f(n.group(0)))


def _f(s: str) -> float:
    return float(s.replace(",", ""))


def _read(path: Path) -> str:
    if not path.exists():
        raise MissingValue(f"{path} is missing")
    return path.read_text()


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _rows(text: str, start: str | None = None) -> list[list[str]]:
    """Table rows (cells) of the first table after the heading ``start``."""
    lines = text.splitlines()
    i = 0
    if start is not None:
        i = next((k for k, ln in enumerate(lines) if ln.startswith(start)), -1)
        if i < 0:
            raise MissingValue(f"section {start!r} not found")
    block: list[str] = []
    for ln in lines[i + 1 :]:
        if ln.startswith("|"):
            block.append(ln)
        elif block or (ln.startswith("## ") and start is not None):
            break

    def sep(ln: str) -> bool:
        return set(ln.replace("|", "").strip()) <= set("- :")

    if len(block) > 1 and sep(block[1]):
        block = block[2:]  # header and separator (the table started after ``start``)
    return [_cells(ln) for ln in block if not sep(ln)]


def _test_page(kind: str, ds: str) -> str:
    return _read(DOCS / "eval" / "test" / f"{kind}_{ds}.md")


# --------------------------------------------------------------------------- X1
LADDER = {
    "S0": "S0 (no sharing)",
    "S1": "S1 tokens",
    "S2": "S2 minimised",
    "S4": "S4 records",
    "oracle": "Oracle (pooled, preregistered)",
    "relational": "Relational oracle",
}


def ladder(ds: str, track: str = "") -> dict[str, CI]:
    """Linked detection per configuration (test), from the X1 page of ``ds``."""
    rows = _rows(_test_page("x1", ds + track), "## Linked detection per configuration")
    out = {}
    for key, prefix in LADDER.items():
        row = next((r for r in rows if r[0].startswith(prefix)), None)
        if row is not None:
            out[key] = CI.parse(row[1])
    if "S0" not in out or "S2" not in out:
        raise MissingValue(f"ladder rows missing on x1_{ds}{track}")
    return out


def gain(ds: str, track: str = "") -> CI:
    """S2 − S0 linked detection (paired, test)."""
    rows = _rows(_test_page("x1", ds + track), "## Linked detection per configuration")
    row = next(r for r in rows if r[0].startswith(LADDER["S2"]))
    return CI.parse(row[4])


def recovery(ds: str, track: str = "") -> CI:
    """S2's share of the relational oracle's gain over S0 (H1b, test)."""
    rows = _rows(_test_page("x1", ds + track), "## H1b on test")
    row = next(r for r in rows if r[0] == "S2")
    return CI.parse(row[1])


# --------------------------------------------------------------------------- audit
TARGETS = {
    "A2_third_party": "## A2 third-member relationship",
    "A3_amount_top": "## A3 amount in top decile",
    "A3_fan_in_top": "## A3 fan-in in top decile",
    "A3_pass_through": "## A3 pass-through account",
}


def attack_advantage(ds: str, target: str = "A3_fan_in_top") -> dict[str, CI]:
    """(attack − prior) TPR at 1% FPR per level on one target (A15 margin quantity)."""
    rows = _rows(_test_page("audit", ds), TARGETS[target])
    return {r[0]: CI.parse(r[4]) for r in rows if r[0] != "prior" and r[4] != "—"}


def pt2(ds: str) -> float:
    m = re.search(r"protocol budget: \*\*(" + _NUM + r")\*\*", _test_page("audit", ds))
    if not m:
        raise MissingValue(f"PT2 ratio not on audit_{ds}")
    return _f(m.group(1))


# --------------------------------------------------------------------------- results pages
def _results_row(ds: str, rule: str) -> list[str]:
    path = DOCS / "eval" / ("a25/RESULTS_LARGE.md" if ds in LARGE else "test/RESULTS.md")
    text = _read(path)
    rows = _rows(text, f"## {ds}")
    row = next((r for r in rows if r[0].split(" (")[0] == rule), None)
    if row is None:
        raise MissingValue(f"rule {rule} not on the results page of {ds}")
    return row


def verdict(ds: str, rule: str) -> bool | None:
    v = _results_row(ds, rule)[3]
    return True if v.startswith("**yes") else (False if v.startswith("**no") else None)


def h1d_best(ds: str) -> tuple[str, CI, float] | None:
    """The PD configuration meeting H1d with the least disclosure: (τ, gain share, disclosure)."""
    text = _results_row(ds, "H1d-L" if ds in LARGE else "H1d")[1]
    best = None
    for tau, g, disc in re.findall(
        rf"PD\[tau=(\d)\]: gain ({_NUM} \[{_NUM}, {_NUM}\]), disclosure ({_NUM})", text
    ):
        share, d = CI.parse(g), _f(disc)
        if share.est >= 0.80 and d < 0.5 and (best is None or d < best[2]):
            best = (tau, share, d)
    return best


def h3a(ds: str) -> bool | None:
    return verdict(ds, "H3a")


def h3b(ds: str) -> CI:
    text = _results_row(ds, "H3b")[1]
    return CI.parse(text.split("grounding", 1)[1])


def case_quality(ds: str) -> dict[str, tuple[float, float]]:
    """S2 vs S0: completeness, fragmentation, alerts per linked scheme (Large tests)."""
    text = _results_row(ds, "Case quality")[1]
    out = {}
    for key, name in (
        ("completeness", "completeness"),
        ("fragmentation", "fragmentation"),
        ("alerts", "alerts per linked scheme"),
    ):
        m = re.search(rf"{name} ({_NUM}) vs ({_NUM})", text)
        if not m:
            raise MissingValue(f"{name} not in the case-quality row of {ds}")
        out[key] = (_f(m.group(1)), _f(m.group(2)))
    return out


def case_quality_diff(ds: str) -> dict[str, CI]:
    text = _results_row(ds, "Case quality")[1]
    out = {}
    for key in ("completeness", "fragmentation"):
        m = re.search(rf"differences.*?{key} ({_NUM} \[{_NUM}, {_NUM}\])", text)
        if m:
            out[key] = CI.parse(m.group(1))
    return out


def flag_within(ds: str) -> bool | None:
    """The protected flag's H1c margin verdict on test (all assessable targets)."""
    text = _results_row(ds, "Protected flag S1F[gate=2]")[1]
    m = re.search(r"H1c margin \*\*(yes|no)\*\*", text)
    return None if not m else m.group(1) == "yes"


def flag_share(ds: str) -> CI:
    text = _results_row(ds, "Protected flag S1F[gate=2]")[1]
    return CI.parse(text.split("gain", 1)[1])


# --------------------------------------------------------------------------- datasets
@dataclass(frozen=True)
class DatasetStats:
    name: str
    transactions: int
    laundering: int
    accounts: int
    days: float
    schemes: int
    test_multi_member: int


def dataset_stats(ds: str) -> DatasetStats:
    g0 = _read(DOCS / "gates" / f"G0_evidence_{ds}.md")
    part = {r[0]: (_f(r[1]), _f(r[2])) for r in _rows(g0, "| Partition | Rows | Laundering rows")}
    if not {"train", "val", "test"} <= set(part):
        raise MissingValue(f"partition rows missing on G0_evidence_{ds}")
    inside = [v for k, v in part.items() if k != "outside"]  # the observation window
    tx = sum(v[0] for v in inside)
    laund = sum(v[1] for v in inside)
    schemes = re.search(r"Schemes: (" + _NUM + ")", g0)
    multi = re.search(r"\*\*(" + _NUM + r")\*\* test schemes touch", g0)
    hours = [_f(r[3]) for r in _rows(g0, "| Period | Start | End | Hours")]
    profile = _read(DOCS / "data_profile" / f"{ds}.md")
    acc = re.search(r"transactions between (" + _NUM + ") accounts", profile)
    if not (schemes and multi and acc):
        raise MissingValue(f"dataset statistics incomplete for {ds}")
    return DatasetStats(
        ds,
        int(tx),
        int(laund),
        int(_f(acc.group(1))),
        sum(hours) / 24,
        int(_f(schemes.group(1))),
        int(_f(multi.group(1))),
    )


# --------------------------------------------------------------------------- benchmark
def benchmark() -> dict[str, dict[str, str]]:
    """Model -> dataset -> cell text, from the benchmark table page."""
    text = _read(DOCS / "eval" / "a25" / "benchmark_table.md")
    lines = [ln for ln in text.splitlines() if ln.startswith("|")]
    head = _cells(lines[0])[1:]
    out = {}
    for ln in lines[2:]:
        c = _cells(ln)
        out[c[0]] = dict(zip(head, c[1:], strict=True))
    return out


# --------------------------------------------------------------------------- narrative
def narrative_page(name: str) -> tuple[CI, CI]:
    """(grounding H3b, strict grounding) of a narrative page under docs/eval/a25."""
    text = _read(DOCS / "eval" / "a25" / f"{name}.md")
    g = re.search(r"\| Grounded first replies \[95% Wilson CI\] \| ([^|]+)\|", text)
    s = re.search(r"\| Strictly grounded first replies \[95% Wilson CI\] \| ([^|]+)\|", text)
    if not (g and s):
        raise MissingValue(f"grounding rows missing on {name}")
    return CI.parse(g.group(1)), CI.parse(s.group(1))


def judge() -> dict[str, tuple[int, int]]:
    """Candidate -> (delivered faithful, of 30) from the LLM-judge page."""
    text = _read(DOCS / "eval" / "a25" / "narrative_judge_A25N.md")
    out = {}
    for row in _rows(text, "## Ratings"):
        m = re.search(r"(\d+) \((\d+)%\)", row[3].replace("**", ""))
        if m:
            out[row[0].replace("**", "").replace("`", "")] = (int(m.group(1)), 30)
    return out


__all__ = [
    "CI",
    "DATASETS",
    "LABEL",
    "LARGE",
    "MEDIUM",
    "MissingValue",
    "attack_advantage",
    "benchmark",
    "case_quality",
    "dataset_stats",
    "gain",
    "judge",
    "ladder",
    "narrative_page",
    "pt2",
    "recovery",
    "verdict",
]
