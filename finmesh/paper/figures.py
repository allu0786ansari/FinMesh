"""The paper's figures, in IEEE format.

IEEE conference layout (IEEEtran): one column is 3.5 in wide, the full text width 7.16 in.
Figures use a Times-compatible serif at 8 pt (7 pt ticks), 0.5 pt axes, and embed their
fonts as TrueType (``pdf.fonttype`` 42), as IEEE PDF checks require. They are saved as
vector PDF (and a 300 dpi PNG preview).

Colour: the sharing levels form an ordinal scale (more sharing = darker), drawn from one
blue ramp (validated as an ordinal ramp on white), so S0 and S2 keep the same colour in
every figure and the levels stay distinguishable in greyscale print. Categorical
distinctions (dataset, track) use the first three slots of the reference categorical
palette together with a marker shape, so identity never rests on colour alone.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from finmesh.paper import sources as S

SINGLE, DOUBLE = 3.5, 7.16  # inches
LEVEL_COLOUR = {"S0": "#86b6ef", "S1": "#3987e5", "S2": "#1c5cab", "relational": "#0d366b"}
CATEGORICAL = ("#2a78d6", "#eb6834", "#1baf7a")
MARKERS = ("o", "s", "^")
INK, INK2, GRID = "#0b0b0b", "#52514e", "#dcdbd7"
MARGIN = 0.05  # H1c (A15)


def style() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Liberation Serif", "Nimbus Roman", "STIXGeneral"],
            "mathtext.fontset": "stix",
            "font.size": 8,
            "axes.labelsize": 8,
            "axes.titlesize": 8,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "legend.fontsize": 7,
            "axes.linewidth": 0.5,
            "xtick.major.width": 0.5,
            "ytick.major.width": 0.5,
            "xtick.major.size": 2.5,
            "ytick.major.size": 2.5,
            "axes.edgecolor": INK2,
            "axes.labelcolor": INK,
            "xtick.color": INK2,
            "ytick.color": INK2,
            "text.color": INK,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.color": GRID,
            "grid.linewidth": 0.4,
            "axes.axisbelow": True,
            "legend.frameon": False,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "savefig.dpi": 300,
            "savefig.bbox": None,  # exact column width: text prints at its set size
            "figure.constrained_layout.use": True,
            "figure.constrained_layout.h_pad": 0.02,
            "figure.constrained_layout.w_pad": 0.02,
        }
    )


def _save(fig: Any, out: Path, name: str) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    paths = [out / f"{name}.pdf", out / f"{name}.png"]
    for p in paths:
        # no creation date in the PDF, so that a rebuild from the same pages is byte-identical
        meta = {"CreationDate": None} if p.suffix == ".pdf" else {}
        fig.savefig(p, metadata=meta)
    plt.close(fig)
    return paths


def _err(ci: S.CI) -> tuple[list[float], list[float]]:
    lo = ci.est - (ci.lo if ci.lo is not None else ci.est)
    hi = (ci.hi if ci.hi is not None else ci.est) - ci.est
    return [max(lo, 0.0)], [max(hi, 0.0)]


# --------------------------------------------------------------------------- Fig. 1
def ladder(out: Path) -> tuple[list[Path], dict[str, Any]]:
    """Linked scheme detection by sharing level, four sealed tests (single column)."""
    levels = (
        ("S0", "S0 local only"),
        ("S1", "S1 tokens + flags"),
        ("S2", "S2 minimised records"),
        ("relational", "Pooled relational oracle"),
    )
    data = {ds: S.ladder(ds) for ds in S.DATASETS}
    fig, ax = plt.subplots(figsize=(SINGLE, 2.15))
    width = 0.19
    for j, (key, label) in enumerate(levels):
        xs = [i + (j - 1.5) * (width + 0.012) for i in range(len(S.DATASETS))]
        for x, ds in zip(xs, S.DATASETS, strict=True):
            ci = data[ds][key]
            ax.bar(
                x,
                ci.est,
                width,
                color=LEVEL_COLOUR[key],
                edgecolor="white",
                linewidth=0.4,
                label=label if ds == S.DATASETS[0] else None,
                zorder=2,
            )
            lo, hi = _err(ci)
            ax.errorbar(
                x,
                ci.est,
                yerr=[lo, hi],
                fmt="none",
                ecolor=INK,
                elinewidth=0.5,
                capsize=1.2,
                capthick=0.5,
                zorder=3,
            )
    ax.set_xticks(range(len(S.DATASETS)), [S.LABEL[d] for d in S.DATASETS])
    ax.set_ylabel("Linked scheme detection")
    ax.set_ylim(0, 1.0)
    ax.grid(axis="x", visible=False)
    ax.tick_params(axis="x", length=0)
    ax.axvline(1.5, color=GRID, linewidth=0.6, zorder=1)
    ax.text(
        0.5,
        0.965,
        "Primary tests",
        ha="center",
        va="top",
        fontsize=7,
        color=INK2,
        transform=ax.get_xaxis_transform(),
    )
    ax.text(
        2.5,
        0.965,
        "Replication tests",
        ha="center",
        va="top",
        fontsize=7,
        color=INK2,
        transform=ax.get_xaxis_transform(),
    )
    ax.legend(
        ncol=2, loc="upper center", bbox_to_anchor=(0.5, 1.30), handlelength=1.0, columnspacing=1.0
    )
    used = {ds: {k: data[ds][k].__dict__ for k, _ in levels} for ds in S.DATASETS}
    return _save(fig, out, "fig_ladder"), used


# --------------------------------------------------------------------------- Fig. 2
PRIVACY_LEVELS = (
    ("S1", "S1 (plain flag)"),
    ("S1F[gate=2]", "S1, gated flag"),
    ("S3[eps=0.5]", r"S3, $\varepsilon$ = 0.5"),
    ("S3[eps=1]", r"S3, $\varepsilon$ = 1"),
    ("S3[eps=2]", r"S3, $\varepsilon$ = 2"),
    ("PD[tau=2]", r"PD, $\tau$ = 2"),
    ("PD[tau=3]", r"PD, $\tau$ = 3"),
    ("PD[tau=4]", r"PD, $\tau$ = 4"),
    ("S2", "S2 (records)"),
)


def privacy(out: Path) -> tuple[list[Path], dict[str, Any]]:
    """Attack advantage on the binding target (fan-in), Large tests (single column)."""
    xmax = 0.10
    data = {ds: S.attack_advantage(ds, "A3_fan_in_top") for ds in S.LARGE}
    fig, ax = plt.subplots(figsize=(SINGLE, 2.45))
    n = len(PRIVACY_LEVELS)
    for k, ds in enumerate(S.LARGE):
        for i, (key, _) in enumerate(PRIVACY_LEVELS):
            ci = data[ds][key]
            y = n - 1 - i + (0.15 if k == 0 else -0.15)
            if ci.est > xmax:
                continue  # off scale: labelled once for the row below
            lo, hi = _err(ci)
            ax.errorbar(
                ci.est,
                y,
                xerr=[lo, hi],
                fmt=MARKERS[k],
                color=CATEGORICAL[k],
                markersize=3.2,
                elinewidth=0.6,
                capsize=1.2,
                capthick=0.5,
                markeredgewidth=0.4,
                markeredgecolor="white",
                zorder=3,
            )
    off = [
        (S.LABEL[ds], data[ds][key].est)
        for ds in S.LARGE
        for key, _ in PRIVACY_LEVELS
        if data[ds][key].est > xmax
    ]
    for i, (key, _) in enumerate(PRIVACY_LEVELS):
        vals = [f"{data[ds][key].est:.2f}" for ds in S.LARGE if data[ds][key].est > xmax]
        if vals:
            ax.text(
                xmax * 0.985,
                n - 1 - i,
                "off scale: " + " / ".join(vals) + r" $\rightarrow$",
                ha="right",
                va="center",
                fontsize=6.5,
                color=INK2,
            )
    del off
    ax.axvline(MARGIN, color=INK, linestyle=(0, (3, 2)), linewidth=0.6, zorder=2)
    ax.text(MARGIN + 0.0015, n - 0.62, "H1c margin", fontsize=6.5, color=INK, va="bottom")
    ax.axvline(0, color=INK2, linewidth=0.5, zorder=1)
    ax.set_yticks(range(n), [lbl for _, lbl in reversed(PRIVACY_LEVELS)])
    ax.set_xlim(-0.012, xmax)
    ax.set_ylim(-0.6, n - 0.2)
    ax.set_xlabel("Attack advantage over prior (TPR at 1% FPR)")
    ax.grid(axis="y", visible=False)
    ax.tick_params(axis="y", length=0)
    handles = [
        Line2D(
            [],
            [],
            marker=MARKERS[k],
            color=CATEGORICAL[k],
            linestyle="none",
            markersize=3.5,
            label=S.LABEL[ds],
        )
        for k, ds in enumerate(S.LARGE)
    ]
    ax.legend(
        handles=handles, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, handletextpad=0.3
    )
    used = {ds: {k: data[ds][k].__dict__ for k, _ in PRIVACY_LEVELS} for ds in S.LARGE}
    return _save(fig, out, "fig_privacy"), used


# --------------------------------------------------------------------------- Fig. 3
def workload(out: Path) -> tuple[list[Path], dict[str, Any]]:
    """Alerts an analyst reviews per linked scheme, S0 vs S2, Large tests (single column)."""
    data = {ds: S.case_quality(ds)["alerts"] for ds in S.LARGE}  # (S2, S0)
    fig, ax = plt.subplots(figsize=(SINGLE, 1.75))
    width = 0.34
    for i, ds in enumerate(S.LARGE):
        s2, s0 = data[ds]
        for x, v, key, label in (
            (i - width / 2 - 0.01, s0, "S0", "S0 local only"),
            (i + width / 2 + 0.01, s2, "S2", "S2 minimised records"),
        ):
            ax.bar(
                x,
                v,
                width,
                color=LEVEL_COLOUR[key],
                edgecolor="white",
                linewidth=0.4,
                label=label if i == 0 else None,
                zorder=2,
            )
            ax.text(x, v * 1.12, f"{v:,.0f}", ha="center", va="bottom", fontsize=6.5, color=INK)
        ax.text(
            i,
            max(s0, s2) * 2.6,
            f"{s0 / s2:.1f}$\\times$ fewer",
            ha="center",
            fontsize=6.5,
            color=INK2,
        )
    ax.set_yscale("log")
    ax.set_ylim(5, 20000)
    ax.set_xticks(range(len(S.LARGE)), [S.LABEL[d] for d in S.LARGE])
    ax.set_xlim(-0.6, 1.6)
    ax.set_ylabel("Alerts per linked scheme")
    ax.grid(axis="x", visible=False)
    ax.tick_params(axis="x", length=0)
    ax.legend(loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.22), handlelength=1.0)
    used = {ds: {"S2": data[ds][0], "S0": data[ds][1]} for ds in S.LARGE}
    return _save(fig, out, "fig_workload"), used


# --------------------------------------------------------------------------- Fig. 4
TRACKS = (("", "Main detector"), ("_noart", "No artefact features"), ("_plus", "Stronger detector"))


def robustness(out: Path) -> tuple[list[Path], dict[str, Any]]:
    """Sharing gain S2 − S0 with 95% CIs across tests and tracks (single column)."""
    rows: list[tuple[str, int, S.CI]] = []
    for ds in S.MEDIUM:
        rows.append((S.LABEL[ds], 0, S.gain(ds)))
    for ds in S.LARGE:
        for k, (suffix, _) in enumerate(TRACKS):
            rows.append((S.LABEL[ds], k, S.gain(ds, suffix)))
    fig, ax = plt.subplots(figsize=(SINGLE, 2.3))
    n = len(rows)
    labels = []
    for i, (name, k, ci) in enumerate(rows):
        y = n - 1 - i
        lo, hi = _err(ci)
        ax.errorbar(
            ci.est,
            y,
            xerr=[lo, hi],
            fmt=MARKERS[k],
            color=CATEGORICAL[k],
            markersize=3.4,
            elinewidth=0.6,
            capsize=1.2,
            capthick=0.5,
            markeredgewidth=0.4,
            markeredgecolor="white",
            zorder=3,
        )
        labels.append(name)
    ax.axvline(0, color=INK2, linewidth=0.5)
    ax.set_yticks(range(n), list(reversed(labels)))
    ax.set_xlim(-0.02, 0.75)
    ax.set_ylim(-0.6, n - 0.4)
    ax.set_xlabel(r"Sharing gain in linked detection, S2 $-$ S0 (95% CI)")
    ax.grid(axis="y", visible=False)
    ax.tick_params(axis="y", length=0)
    ax.axhline(n - 2.5, color=GRID, linewidth=0.6)
    handles = [
        Line2D(
            [],
            [],
            marker=MARKERS[k],
            color=CATEGORICAL[k],
            linestyle="none",
            markersize=3.5,
            label=lbl,
        )
        for k, (_, lbl) in enumerate(TRACKS)
    ]
    ax.legend(
        handles=handles,
        loc="lower center",
        bbox_to_anchor=(0.45, 1.0),
        ncol=3,
        handletextpad=0.2,
        columnspacing=0.9,
    )
    used = {f"{name} {TRACKS[k][1]}": ci.__dict__ for name, k, ci in rows}
    return _save(fig, out, "fig_robustness"), used


def build(out: Path) -> dict[str, Any]:
    style()
    numbers: dict[str, Any] = {}
    files: list[Path] = []
    for fn in (ladder, privacy, workload, robustness):
        paths, used = fn(out)
        files += paths
        numbers[fn.__name__] = used
    return {"files": [str(p) for p in files], "numbers": numbers}


__all__ = ["DOUBLE", "SINGLE", "build", "style"]
