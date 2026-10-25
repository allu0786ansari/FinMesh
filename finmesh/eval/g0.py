"""Gate G0 evidence: is the headline sharing study (RQ1) feasible on this data?

Proposal Section 7.3 asks for the number of pattern-labelled test schemes that
touch two or more federation members, and decides by preregistered bands:
100 or more proceed; 40 to 99 proceed with pooled federations and RQ1 as a
case study; under 40 fall back (HI-Medium, or lead with RQ2 and RQ3).

Week 1 showed that the federation definition itself must be chosen (finding 3).
Amendment A5 (25 Oct 2026, after the first real G0 run) fixes it by design:

* **Primary federation: B8**, all bank IDs grouped into eight institutions
  balanced by accounts. Every account belongs to a member, as in a national
  partnership of the largest banks, and it is the proposal's "four to eight"
  members. Test schemes are counted for B8 only.
* **Real-bank options (A8-A64) are a secondary analysis** of partial
  participation: what changes when the consortium holds only a few percent of
  accounts. They are reported on train and validation schemes only.

A5 replaces the week-2 rule (choose the smallest real-bank option projecting
100 test schemes). That rule projected from train and validation together,
which overstates the test count: train schemes are rarely cut by a partition
end, while validation and test schemes often are, and sparse real-bank
federations lose the few legs they can see. On HI-Medium it chose A64 on a
projection of 135, and the test count was 87. The bias is visible in train
and validation alone (A64: 2.1 multi-member schemes per hour in train, 1.3 in
validation), so projections now use the validation rate only.

A scheme is visible to a member when one of its in-partition transactions
touches one of that member's accounts. Transactions masked in a partition
(they belong to a scheme assigned elsewhere) are never counted.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import polars as pl

from finmesh.data.consortium import (
    CANDIDATES,
    DEFAULT_GROUPED,
    ConsortiumSpec,
    bank_sizes,
    build_membership,
    membership_summary,
)
from finmesh.data.manifest import load_manifest
from finmesh.data.schema import FIXTURE_DATASET
from finmesh.data.splits import (
    SplitPlan,
    assign_schemes,
    choose_window_hours,
    detect_observation_window,
    partition_expr,
    plan_split,
    scheme_transactions,
    transaction_split,
    window_activity,
)
from finmesh.data.visibility import (
    LEG_KINDS,
    account_share,
    attach_members,
    coverage,
    leg_kind_expr,
    visible_members_expr,
)
from finmesh.eval.provenance import Stamp, write_artifact
from finmesh.paths import DatasetPaths, artifacts_dir
from finmesh.reporting import fmt, table
from finmesh.sysinfo import AnonPeak, timed

PROCEED_THRESHOLD = 100
CASE_STUDY_THRESHOLD = 40


def band(test_multi_member_schemes: int) -> str:
    if test_multi_member_schemes >= PROCEED_THRESHOLD:
        return "proceed"
    if test_multi_member_schemes >= CASE_STUDY_THRESHOLD:
        return "case_study_pooled"
    return "fallback"


BAND_TEXT = {
    "proceed": "Proceed with RQ1 as the headline on this dataset.",
    "case_study_pooled": (
        "Proceed; pool both federations for headline estimates and report RQ1 with wide "
        "intervals as a case study alongside RQ2."
    ),
    "fallback": (
        "Fall back: try HI-Medium with the same membership rule if it fits in memory; "
        "otherwise lead with RQ2 and RQ3 and report RQ1 as exploratory."
    ),
}


@dataclass(frozen=True)
class OptionResult:
    spec: ConsortiumSpec
    members: int
    member_account_share: float | None
    visible_tx_share: float | None
    multi_member: dict[str, int]  # partition -> schemes visible to >= 2 members
    visible: dict[str, int]  # partition -> schemes visible to >= 1 member
    legs: dict[str, int]  # leg kind -> scheme transactions (train + val)
    projected_test_multi_member: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "option": self.spec.name,
            "members": self.members,
            "member_account_share": self.member_account_share,
            "visible_tx_share": self.visible_tx_share,
            "multi_member": self.multi_member,
            "visible": self.visible,
            "scheme_legs_train_val": self.legs,
            "projected_test_multi_member": round(self.projected_test_multi_member, 1),
        }


def _own_rows(scheme_tx: pl.DataFrame, assignment: pl.DataFrame) -> pl.DataFrame:
    """Scheme transactions that fall in the scheme's own (assigned) partition."""
    return scheme_tx.join(
        assignment.select("scheme_id", pl.col("partition").alias("scheme_partition")),
        on="scheme_id",
    ).filter(pl.col("tx_partition") == pl.col("scheme_partition"))


def scheme_visibility(own: pl.DataFrame, membership: pl.DataFrame) -> pl.DataFrame:
    """Per scheme: its partition and how many members can see it."""
    with_m = attach_members(own.lazy(), membership).collect()
    return (
        with_m.group_by("scheme_id")
        .agg(
            pl.col("scheme_partition").first().alias("partition"),
            pl.col("pattern").first(),
            visible_members_expr().alias("members_visible"),
        )
        .with_columns(pl.col("members_visible").list.len().alias("n_members"))
    )


def _counts(vis: pl.DataFrame, partitions: tuple[str, ...], minimum: int) -> dict[str, int]:
    out = {}
    for p in partitions:
        out[p] = int(
            vis.filter((pl.col("partition") == p) & (pl.col("n_members") >= minimum)).height
        )
    return out


def evaluate_option(
    spec: ConsortiumSpec,
    sizes: pl.DataFrame,
    own: pl.DataFrame,
    window_lf: pl.LazyFrame,
    plan: SplitPlan,
) -> tuple[OptionResult, pl.DataFrame, pl.DataFrame]:
    membership = build_membership(sizes, spec)
    vis = scheme_visibility(own, membership)
    trainval = ("train", "val")
    multi = _counts(vis, trainval, 2)
    visible = _counts(vis, trainval, 1)
    legs_df = (
        attach_members(own.filter(pl.col("scheme_partition") != "test").lazy(), membership)
        .group_by(leg_kind_expr().alias("kind"))
        .agg(pl.len().alias("n"))
        .collect()
    )
    legs = {k: 0 for k in LEG_KINDS}
    legs.update({str(k): int(n) for k, n in legs_df.iter_rows()})
    cov = coverage(attach_members(window_lf, membership))
    acc = account_share(sizes, membership)
    # Validation rate only (A5): validation schemes, like test schemes, are cut
    # by a partition end; train schemes mostly are not.
    projected = multi["val"] * plan.period("test").hours / plan.period("val").hours
    result = OptionResult(
        spec=spec,
        members=int(membership["member"].n_unique()),
        member_account_share=acc["member_account_share"],
        visible_tx_share=cov["visible_share"],
        multi_member=multi,
        visible=visible,
        legs=legs,
        projected_test_multi_member=projected,
    )
    return result, membership, vis


def select_option(results: list[OptionResult]) -> tuple[ConsortiumSpec, str]:
    """Amendment A5: the primary federation is fixed by design, not chosen from counts."""
    del results  # kept in the signature: every option is still evaluated and reported
    return DEFAULT_GROUPED, (
        f"primary federation fixed by design (amendment A5): {DEFAULT_GROUPED.name}, "
        "eight institutions covering every account; real-bank options are a secondary "
        "partial-participation analysis"
    )


def account_overlap(own: pl.DataFrame, earlier: tuple[str, ...], later: str) -> dict[str, Any]:
    """Share of a later partition's scheme accounts already seen in earlier schemes."""

    def accounts(parts: tuple[str, ...]) -> set[str]:
        sub = own.filter(pl.col("scheme_partition").is_in(list(parts)))
        return set(sub["src_key"].to_list()) | set(sub["dst_key"].to_list())

    seen, now = accounts(earlier), accounts((later,))
    shared = len(now & seen)
    return {
        "partition": later,
        "compared_with": list(earlier),
        "accounts": len(now),
        "seen_before": shared,
        "share_seen_before": shared / len(now) if now else None,
    }


def run_g0(paths: DatasetPaths, write_split: bool = True) -> dict[str, Any]:
    """Compute all G0 evidence for one dataset; return the result payload."""
    timings: dict[str, float] = {}
    with AnonPeak() as anon:
        with timed(timings, "window_and_split_s"):
            observation = detect_observation_window(paths.transactions)
            window_hours, window_table = choose_window_hours(observation)
            plan = plan_split(observation, window_hours)
            plan.write(paths.parquet / "split_plan.json")
            activity = window_activity(paths.transactions, observation)
            schemes = pl.read_parquet(paths.schemes)
            scheme_tx = scheme_transactions(paths.transactions, paths.scheme_links, plan)
            scheme_tx = scheme_tx.join(schemes.select("scheme_id", "pattern"), on="scheme_id")
            assignment = assign_schemes(scheme_tx, schemes, plan)
            if write_split:
                transaction_split(
                    paths.transactions, paths.scheme_links, assignment, plan
                ).sink_parquet(paths.parquet / f"split_w{window_hours}.parquet", compression="zstd")
                assignment.write_parquet(
                    paths.parquet / f"scheme_assignment_w{window_hours}.parquet"
                )
        own = _own_rows(scheme_tx, assignment)
        window_lf = pl.scan_parquet(paths.transactions).filter(
            (pl.col("timestamp") >= observation.start) & (pl.col("timestamp") < observation.end)
        )
        with timed(timings, "options_s"):
            sizes = bank_sizes(paths.transactions)
            evaluated = [evaluate_option(s, sizes, own, window_lf, plan) for s in CANDIDATES]
        results = [r for r, _, _ in evaluated]
        chosen, reason = select_option(results)
        _, chosen_membership, chosen_vis = next(e for e in evaluated if e[0].spec == chosen)
        chosen_membership.write_parquet(paths.parquet / f"membership_{chosen.name}.parquet")

        # Step 3: the test set is opened for the chosen option only.
        test_multi = int(
            chosen_vis.filter((pl.col("partition") == "test") & (pl.col("n_members") >= 2)).height
        )
        test_visible = int(
            chosen_vis.filter((pl.col("partition") == "test") & (pl.col("n_members") >= 1)).height
        )

    by_partition = (
        assignment.group_by("partition")
        .agg(
            pl.len().alias("schemes"),
            pl.col("truncated").sum().alias("truncated"),
            pl.col("rows_in_partition").sum().alias("scheme_rows_in_partition"),
        )
        .with_columns(pl.col("partition").cast(pl.String))
        .sort("partition")
    )
    patterns = (
        chosen_vis.filter(pl.col("n_members") >= 2)
        .with_columns(pl.col("partition").cast(pl.String))
        .group_by("pattern", "partition")
        .len()
        .pivot(on="partition", index="pattern", values="len")
        .fill_null(0)
        .sort("pattern")
    )
    split_table = (
        pl.scan_parquet(paths.transactions)
        .select("timestamp", "is_laundering")
        .with_columns(partition_expr(plan).cast(pl.String).alias("partition"))
        .group_by("partition")
        .agg(pl.len().alias("rows"), pl.col("is_laundering").sum().alias("laundering_rows"))
        .sort("partition")
        .collect(engine="streaming")
    )

    return {
        "dataset": paths.name,
        "observation_window": observation.to_dict(),
        "window_rule": window_table,
        "window_hours": window_hours,
        "window_activity": activity,
        "split_plan": plan.to_dict(),
        "rows_by_partition": split_table.to_dicts(),
        "schemes_by_partition": by_partition.to_dicts(),
        "schemes_total": assignment.height,
        "schemes_truncated": int(assignment["truncated"].sum()),
        "bank_sizes_top": sizes.head(20).to_dicts(),
        "banks": sizes.height,
        "options": [r.to_dict() for r in results],
        "selection": {"option": chosen.name, "reason": reason},
        "chosen_membership": membership_summary(sizes, chosen_membership).to_dicts(),
        "test": {
            "option": chosen.name,
            "multi_member_schemes": test_multi,
            "visible_schemes": test_visible,
            "band": band(test_multi),
            "band_text": BAND_TEXT[band(test_multi)],
        },
        "multi_member_patterns_chosen": patterns.to_dicts(),
        "account_overlap": [
            account_overlap(own, ("train",), "val"),
            account_overlap(own, ("train", "val"), "test"),
        ],
        "thresholds": {"proceed": PROCEED_THRESHOLD, "case_study": CASE_STUDY_THRESHOLD},
        "timings": timings,
        "peak_anon_mb": anon.mb,
    }


def render(result: dict[str, Any]) -> str:
    """Markdown evidence page for one dataset."""
    ow = result["observation_window"]
    sp = result["split_plan"]
    t = result["test"]
    lines = [
        f"# G0 evidence · {result['dataset']}",
        "",
        f"**Outcome:** option **{t['option']}** ({result['selection']['reason']}); "
        f"**{t['multi_member_schemes']}** test schemes touch two or more members → "
        f"band **{t['band']}**. {t['band_text']}",
        "",
        "## Observation window",
        "",
        f"{ow['start']} to {ow['end']} (exclusive), {ow['dense_days']} dense days; "
        f"rule: {ow['rule']}. "
        f"Excluded: {fmt(ow['rows_before'])} rows before and {fmt(ow['rows_after'])} rows after "
        f"({fmt(ow['laundering_rows_after'])} of them laundering).",
        "",
        "## Window length",
        "",
        f"Chosen: **{result['window_hours']} h** (largest candidate with at least 8 test windows).",
        "",
        table(
            result["window_rule"],
            [
                ("window_hours", "Hours"),
                ("windows", "Windows"),
                ("train", "Train"),
                ("val", "Val"),
                ("test", "Test"),
                ("meets_rule", "Meets rule"),
            ],
        ),
        "",
        table(
            result["window_activity"],
            [
                ("window_hours", "Hours"),
                ("active_account_windows", "Active account-windows"),
                ("median_tx_per_active_window", "Median tx"),
                ("p90_tx_per_active_window", "P90 tx"),
                ("median_active_windows_per_account", "Median windows per account"),
                ("sample", "Sample"),
            ],
        ),
        "",
        "## Splits",
        "",
        table(
            sp["periods"],
            [("name", "Period"), ("start", "Start"), ("end", "End"), ("hours", "Hours")],
        ),
        "",
        table(
            result["rows_by_partition"],
            [("partition", "Partition"), ("rows", "Rows"), ("laundering_rows", "Laundering rows")],
        ),
        "",
        f"Schemes: {fmt(result['schemes_total'])}, of which "
        f"{fmt(result['schemes_truncated'])} run past the window end "
        "(scored on their in-window part).",
        "",
        table(
            result["schemes_by_partition"],
            [
                ("partition", "Assigned to"),
                ("schemes", "Schemes"),
                ("truncated", "Truncated"),
                ("scheme_rows_in_partition", "Rows in own partition"),
            ],
        ),
        "",
        "## Federation options (train and validation only)",
        "",
        "Multi-member = scheme visible to two or more members within its own partition. "
        "Projected test = (train + val) scaled by the test period's share of time.",
        "",
        table(
            [
                {
                    **o,
                    "mm_train": o["multi_member"]["train"],
                    "mm_val": o["multi_member"]["val"],
                    "vis_train": o["visible"]["train"],
                    "invisible": o["scheme_legs_train_val"]["invisible"],
                    "boundary": o["scheme_legs_train_val"]["boundary"],
                    "cross": o["scheme_legs_train_val"]["cross_member"],
                    "internal": o["scheme_legs_train_val"]["internal"],
                }
                for o in result["options"]
            ],
            [
                ("option", "Option"),
                ("members", "Members"),
                ("member_account_share", "Account share"),
                ("visible_tx_share", "Tx visible"),
                ("vis_train", "Visible (train)"),
                ("mm_train", "Multi (train)"),
                ("mm_val", "Multi (val)"),
                ("projected_test_multi_member", "Projected test"),
                ("invisible", "Legs invisible"),
                ("boundary", "Legs boundary"),
                ("cross", "Legs cross-member"),
                ("internal", "Legs internal"),
            ],
        ),
        "",
        f"**Selection:** {result['selection']['option']} — {result['selection']['reason']}.",
        "",
        "## Test count (chosen option only)",
        "",
        f"{t['multi_member_schemes']} multi-member and {t['visible_schemes']} visible "
        "test schemes. "
        f"Thresholds: {result['thresholds']['proceed']} proceed, "
        f"{result['thresholds']['case_study']} case study.",
        "",
        "Multi-member schemes by pattern and partition (chosen option):",
        "",
        table(
            result["multi_member_patterns_chosen"],
            [
                (k, k)
                for k in (
                    result["multi_member_patterns_chosen"][0].keys()
                    if result["multi_member_patterns_chosen"]
                    else ["pattern"]
                )
            ],
        ),
        "",
        "## Members of the chosen option",
        "",
        table(
            result["chosen_membership"],
            [
                ("member", "Member"),
                ("banks", "Bank IDs"),
                ("accounts", "Accounts"),
                ("tx_touching_upper_bound", "Tx touching (upper bound)"),
                ("largest_bank", "Largest bank"),
            ],
        ),
        "",
        "## Account reuse across partitions",
        "",
        "Launderer accounts that recur in later schemes make detection easier than a fresh "
        "scheme would be; this is reported, not corrected.",
        "",
        table(
            [
                {**a, "compared_with": "+".join(a["compared_with"])}
                for a in result["account_overlap"]
            ],
            [
                ("partition", "Partition"),
                ("compared_with", "Compared with"),
                ("accounts", "Accounts"),
                ("seen_before", "Seen before"),
                ("share_seen_before", "Share"),
            ],
        ),
        "",
        "## Largest banks by accounts",
        "",
        table(
            result["bank_sizes_top"],
            [
                ("rank", "Rank"),
                ("bank", "Bank"),
                ("accounts", "Accounts"),
                ("tx_touching", "Tx touching"),
            ],
        ),
        "",
        f"Resources: {result['timings']}, peak memory {fmt(result['peak_anon_mb'])} MB.",
        "",
    ]
    return "\n".join(lines)


def write_g0(
    paths: DatasetPaths, report_path: Path | None
) -> tuple[Path, Path | None, dict[str, Any]]:
    manifest = load_manifest(paths.manifest)
    result = run_g0(paths)
    stamp = Stamp(
        kind="g0_evidence",
        dataset=paths.name,
        manifest_hash=manifest.manifest_hash,
        fixture=manifest.fixture,
        params={
            "candidates": [c.name for c in CANDIDATES],
            "proceed": PROCEED_THRESHOLD,
            "case_study": CASE_STUDY_THRESHOLD,
        },
        split=f"w{result['window_hours']}",
    )
    artifact = write_artifact(
        artifacts_dir(paths.root) / "week02" / f"g0_{paths.name}.json", stamp, result
    )
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        header = (
            f"<!-- generated by `finmesh g0 --dataset {paths.name}`; manifest "
            f"{manifest.manifest_hash[:12]}; fixture={manifest.fixture} -->\n\n"
        )
        report_path.write_text(header + render(result))
    return artifact, report_path, result


def render_summary(results: list[dict[str, Any]]) -> str:
    rows = [
        {
            "dataset": r["dataset"],
            "option": r["test"]["option"],
            "test_multi": r["test"]["multi_member_schemes"],
            "band": r["test"]["band"],
            "window_hours": r["window_hours"],
            "schemes": r["schemes_total"],
            "days": r["observation_window"]["dense_days"],
        }
        for r in sorted(results, key=lambda r: str(r["dataset"]))
    ]
    lines = [
        "# G0 evidence · summary",
        "",
        table(
            rows,
            [
                ("dataset", "Dataset"),
                ("days", "Dense days"),
                ("schemes", "Schemes"),
                ("window_hours", "Window h"),
                ("option", "Option"),
                ("test_multi", "Multi-member test schemes"),
                ("band", "Band"),
            ],
        ),
        "",
    ]
    # Pool the HI and LI regimes of the same size, when both used the same option.
    sizes: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        sizes.setdefault(str(r["dataset"]).split("-", 1)[-1], []).append(r)
    for size, group in sorted(sizes.items()):
        if len(group) < 2:
            continue
        if len({g["option"] for g in group}) == 1:
            pooled = sum(int(g["test_multi"]) for g in group)
            names = " + ".join(str(g["dataset"]) for g in group)
            lines.append(
                f"Pooled {names} ({group[0]['option']}): **{pooled}** → band **{band(pooled)}**."
            )
        else:
            lines.append(f"{size}: datasets used different options, so counts are not pooled.")
    lines += ["", "The decision note is `docs/gates/G0.md`.", ""]
    return "\n".join(lines)


def load_result(path: Path) -> dict[str, Any]:
    doc: dict[str, Any] = json.loads(path.read_text())
    return dict(doc["result"])


def is_fixture(name: str) -> bool:
    return name == FIXTURE_DATASET
