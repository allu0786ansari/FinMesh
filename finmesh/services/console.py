"""The analyst console (week 16): a local web app over the demo path's durable state.

* **Queue**: each member's closed sessions ranked by fused score; sessions within the
  member's alert budget (1 per 1,000 accounts per day over the replayed span) are marked.
* **Case**: the incident card, the evidence from each responding member (sharing level,
  status, alert flag, record released), the typology hint with its basis, the summary and
  the catalogue's review actions.
* **Actions**: low-impact actions are recorded at once; escalating, freezing an account and
  filing a report wait for a second analyst's approval (four eyes).
* **Privacy ledger**: :func:`finmesh.services.ledger.privacy_ledger`.

It binds to 127.0.0.1 only (see ``finmesh console``); analyst names are typed in the page,
which is enough for a single-machine demo but is not authentication.
"""

from __future__ import annotations

import math
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from finmesh.services.ledger import privacy_ledger
from finmesh.services.store import HIGH_IMPACT, BudgetLedger, SessionStore

ACTIONS = (
    "add_note",
    "monitor",
    "dismiss",
    "request_more_evidence",
    "escalate",
    "freeze_account",
    "file_report",
)
WINDOW_HOURS = 6


class ActionIn(BaseModel):
    action: str
    actor: str = Field(min_length=1, max_length=64)
    note: str = Field(default="", max_length=1000)


class DecisionIn(BaseModel):
    approver: str = Field(min_length=1, max_length=64)
    approve: bool


def _budgets(sessions: list[dict[str, Any]], meta: dict[str, Any]) -> dict[int, int]:
    windows = [s["window"] for s in sessions]
    if not windows:
        return {}
    days = (max(windows) - min(windows) + 1) * WINDOW_HOURS / 24
    apm = meta.get("accounts_per_member", {})
    return {int(m): max(1, math.ceil(a / 1000 * days)) for m, a in apm.items()}


def queue(store: SessionStore, meta: dict[str, Any], member: int | None) -> list[dict[str, Any]]:
    sessions = store.sessions()
    budgets = _budgets(sessions, meta)
    out = []
    for m in sorted({s["member"] for s in sessions}):
        if member is not None and m != member:
            continue
        mine = [s for s in sessions if s["member"] == m]
        mine.sort(key=lambda s: -(s["card"] or {}).get("fused_score", -1.0))
        for rank, s in enumerate(mine, 1):
            card = s["card"] or {}
            pending = sum(a["status"] == "pending_approval" for a in store.actions(s["key"]))
            out.append(
                {
                    "key": s["key"],
                    "member": m,
                    "window": s["window"],
                    "state": s["state"],
                    "rank": rank,
                    "within_budget": rank <= budgets.get(m, len(mine)),
                    "fused_score": card.get("fused_score"),
                    "own_probability": card.get("own_probability"),
                    "peer_alerts": card.get("peer_alerts"),
                    "evidence_incomplete": card.get("evidence_incomplete"),
                    "typology_hint": card.get("typology_hint"),
                    "suggested_action": card.get("suggested_action"),
                    "pending_approvals": pending,
                    "error": s["error"],
                }
            )
    return out


def console_app(store: SessionStore, budget: BudgetLedger | None, meta: dict[str, Any]) -> FastAPI:
    app = FastAPI(title="FinMesh analyst console", docs_url=None, redoc_url=None)

    @app.get("/", response_class=HTMLResponse)
    def page() -> str:
        return PAGE

    @app.get("/api/meta")
    def get_meta() -> dict[str, Any]:
        return {
            "dataset": meta.get("dataset"),
            "level": meta.get("level"),
            "members": meta.get("members", []),
            "actions": list(ACTIONS),
            "high_impact": sorted(HIGH_IMPACT),
        }

    @app.get("/api/queue")
    def get_queue(member: int | None = None) -> list[dict[str, Any]]:
        return queue(store, meta, member)

    @app.get("/api/session/{key}")
    def get_session(key: str) -> dict[str, Any]:
        try:
            s = store.session(key)
        except KeyError as exc:
            raise HTTPException(404, "no such session") from exc
        return {**s, "actions": store.actions(key)}

    @app.post("/api/session/{key}/actions")
    def post_action(key: str, body: ActionIn) -> dict[str, Any]:
        if body.action not in ACTIONS:
            raise HTTPException(400, f"unknown action; use one of {', '.join(ACTIONS)}")
        try:
            return store.record_action(key, body.action, body.actor.strip(), body.note)
        except KeyError as exc:
            raise HTTPException(404, "no such session") from exc

    @app.post("/api/actions/{action_id}/decide")
    def decide(action_id: int, body: DecisionIn) -> dict[str, Any]:
        try:
            return store.decide(action_id, body.approver.strip(), body.approve)
        except KeyError as exc:
            raise HTTPException(404, "no such action") from exc
        except PermissionError as exc:
            raise HTTPException(403, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.get("/api/ledger")
    def get_ledger() -> dict[str, Any]:
        return privacy_ledger(store, budget, meta)

    return app


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FinMesh console</title>
<style>
:root { --bg:#f7f8fa; --panel:#fff; --ink:#1d2433; --muted:#5b6475; --line:#e2e6ee;
  --accent:#2457c5; --warn:#b4540a; --ok:#1d7a46; }
@media (prefers-color-scheme: dark) { :root { --bg:#12151b; --panel:#1b2029; --ink:#e7ebf2;
  --muted:#9aa4b5; --line:#2c3340; --accent:#7aa2ff; --warn:#f0a35e; --ok:#5cc98b; } }
* { box-sizing:border-box } body { margin:0; font:14px/1.45 system-ui,sans-serif;
  background:var(--bg); color:var(--ink) }
header { display:flex; gap:16px; align-items:center; padding:10px 16px;
  border-bottom:1px solid var(--line); background:var(--panel); flex-wrap:wrap }
header h1 { font-size:16px; margin:0 } header .sp { flex:1 }
nav button, .btn { border:1px solid var(--line); background:var(--panel); color:var(--ink);
  padding:5px 10px; border-radius:6px; cursor:pointer } nav button.on { border-color:var(--accent);
  color:var(--accent) }
main { display:grid; grid-template-columns:minmax(260px,360px) 1fr; gap:12px; padding:12px }
@media (max-width:800px) { main { grid-template-columns:1fr } }
.panel { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:12px;
  overflow:auto } .panel h2 { font-size:14px; margin:0 0 8px }
table { border-collapse:collapse; width:100% } td,th { text-align:left; padding:4px 6px;
  border-bottom:1px solid var(--line); vertical-align:top } th { color:var(--muted); font-weight:600 }
tr.row { cursor:pointer } tr.row:hover, tr.sel { background:color-mix(in srgb,var(--accent) 10%,transparent) }
.muted { color:var(--muted) } .warn { color:var(--warn) } .ok { color:var(--ok) }
.tag { display:inline-block; padding:0 6px; border-radius:10px; border:1px solid var(--line);
  font-size:12px } input, select, textarea { font:inherit; color:var(--ink); background:var(--bg);
  border:1px solid var(--line); border-radius:6px; padding:4px 6px }
.grid2 { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:8px }
.kpi { border:1px solid var(--line); border-radius:6px; padding:6px 8px }
.kpi b { display:block; font-size:16px } #ledger { display:none; padding:12px }
</style></head><body>
<header><h1>FinMesh analyst console</h1><span id="meta" class="muted"></span>
<span class="sp"></span>
<label>Member <select id="member"></select></label>
<label>Analyst <input id="analyst" size="10" placeholder="your name"></label>
<nav><button id="tabCases" class="on">Cases</button> <button id="tabLedger">Privacy ledger</button></nav>
</header>
<main id="cases"><section class="panel"><h2>Incident queue</h2><table id="queue"></table></section>
<section class="panel" id="case"><p class="muted">Select an incident.</p></section></main>
<section id="ledger"></section>
<script>
const $ = (s) => document.querySelector(s);
const el = (tag, attrs = {}, ...kids) => { const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) { if (k === "class") e.className = v; else if (k.startsWith("on")) e[k] = v; else e.setAttribute(k, v); }
  for (const k of kids) e.append(k instanceof Node ? k : document.createTextNode(k ?? "")); return e; };
const api = async (path, opts) => { const r = await fetch(path, opts); const j = await r.json();
  if (!r.ok) throw new Error(j.detail || r.statusText); return j; };
const fmt = (v) => v === null || v === undefined ? "—" : (typeof v === "number" ? (Number.isInteger(v) ? v : v.toFixed(3)) : v);
let meta, current;
async function init() {
  meta = await api("/api/meta");
  $("#meta").textContent = `${meta.dataset} · level ${meta.level}`;
  const sel = $("#member"); sel.append(el("option", {value: ""}, "all"));
  for (const m of meta.members) sel.append(el("option", {value: m}, "member " + m));
  sel.onchange = loadQueue; await loadQueue();
}
async function loadQueue() {
  const m = $("#member").value; const rows = await api("/api/queue" + (m ? "?member=" + m : ""));
  const t = $("#queue"); t.replaceChildren(el("tr", {}, el("th", {}, "#"), el("th", {}, "Member"),
    el("th", {}, "Window"), el("th", {}, "Score"), el("th", {}, "Hint")));
  for (const r of rows) {
    const tr = el("tr", {class: "row" + (r.key === current ? " sel" : "")},
      el("td", {}, String(r.rank), r.within_budget ? "" : " ·"), el("td", {}, String(r.member)),
      el("td", {}, String(r.window)), el("td", {}, fmt(r.fused_score)),
      el("td", {}, r.state === "closed" ? (r.typology_hint || "") : r.state,
        r.pending_approvals ? el("span", {class: "tag warn"}, " approval") : "",
        r.evidence_incomplete ? el("span", {class: "tag warn"}, " partial") : ""));
    tr.onclick = () => openCase(r.key); t.append(tr);
  }
}
async function openCase(key) {
  current = key; const s = await api("/api/session/" + encodeURIComponent(key)); const c = s.card || {};
  const box = $("#case"); box.replaceChildren();
  box.append(el("h2", {}, `Incident ${s.key} · ${s.state}`));
  if (s.error) box.append(el("p", {class: "warn"}, s.error));
  box.append(el("div", {class: "grid2"}, ...[["Own probability", c.own_probability], ["Fused score", c.fused_score],
    ["Members asked", c.members_asked], ["Peer alerts", c.peer_alerts], ["Records received", c.peer_records],
    ["Suggested", c.suggested_action]].map(([k, v]) => el("div", {class: "kpi"}, el("span", {class: "muted"}, k), el("b", {}, String(fmt(v)))))));
  if (c.summary) { box.append(el("h2", {}, "Summary"), el("p", {}, c.summary)); }
  if (c.typology_hint) box.append(el("p", {}, el("b", {}, "Typology hint: " + c.typology_hint + " "),
    el("span", {class: "muted"}, "(" + c.typology_hint_basis + ") "), c.typology_description || ""));
  if (c.review_actions) { box.append(el("h2", {}, "Review actions (catalogue)"));
    const ol = el("ol"); for (const a of c.review_actions) ol.append(el("li", {}, a)); box.append(ol); }
  box.append(el("h2", {}, "Evidence from other members"));
  const t = el("table", {}, el("tr", {}, ...["Member", "Epoch", "Level", "Status", "Peer alert", "Record"].map((h) => el("th", {}, h))));
  for (const e of c.evidence || []) t.append(el("tr", {}, el("td", {}, String(e.member)), el("td", {}, String(e.epoch)),
    el("td", {}, e.level || "—"), el("td", {class: e.status === "ok" ? "ok" : (e.status === "unavailable" ? "warn" : "")}, e.status),
    el("td", {}, e.peer_alert ? "yes" : "no"), el("td", {}, e.has_record ? "released" : "—")));
  box.append(t);
  box.append(el("h2", {}, "Actions"));
  const act = el("select"); for (const a of meta.actions) act.append(el("option", {value: a}, a + (meta.high_impact.includes(a) ? " (needs approval)" : "")));
  const note = el("input", {placeholder: "note", size: "30"});
  const msg = el("span", {class: "muted"});
  box.append(el("p", {}, act, " ", note, " ", el("button", {class: "btn", onclick: async () => {
    try { await api(`/api/session/${encodeURIComponent(key)}/actions`, {method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({action: act.value, actor: $("#analyst").value || "", note: note.value})}); openCase(key); loadQueue(); }
    catch (e) { msg.textContent = e.message; } }}, "Record"), " ", msg));
  const at = el("table", {}, el("tr", {}, ...["#", "Action", "By", "Status", "Approver", ""].map((h) => el("th", {}, h))));
  for (const a of s.actions) {
    const cell = el("td");
    if (a.status === "pending_approval") for (const ok of [true, false]) cell.append(el("button", {class: "btn", onclick: async () => {
      try { await api(`/api/actions/${a.id}/decide`, {method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({approver: $("#analyst").value || "", approve: ok})}); openCase(key); loadQueue(); }
      catch (e) { msg.textContent = e.message; } }}, ok ? "Approve" : "Reject"), " ");
    at.append(el("tr", {}, el("td", {}, String(a.id)), el("td", {}, a.action), el("td", {}, a.actor),
      el("td", {class: a.status === "pending_approval" ? "warn" : ""}, a.status), el("td", {}, a.approver || ""), cell));
  }
  box.append(at); loadQueue();
}
async function showLedger() {
  const L = await api("/api/ledger"); const box = $("#ledger"); box.replaceChildren();
  const sec = (title, ...kids) => el("section", {class: "panel", style: "margin-bottom:12px"}, el("h2", {}, title), ...kids);
  box.append(sec("Model", el("p", {}, L.model.note)));
  const ev = el("table", {}, el("tr", {}, ...["Member", "Requests sent", "Requests received", "Records released", "Alert flags", "Refused", "Unavailable"].map((h) => el("th", {}, h))));
  for (const m of L.evidence.by_member) ev.append(el("tr", {}, ...[m.member, m.requests_sent, m.requests, m.records_released, m.alert_flags, m.refused, m.unavailable].map((v) => el("td", {}, String(v)))));
  box.append(sec("Evidence channel (level " + L.level + ")", el("p", {class: "muted"}, L.evidence.note), ev));
  const tk = el("table", {}, el("tr", {}, ...["Bank", "Epoch", "Evaluations", "Budget", "Used", "Refused"].map((h) => el("th", {}, h))));
  for (const t of L.tokens) tk.append(el("tr", {}, ...[t.bank, t.epoch, t.evaluated, t.budget, t.share_used === null ? "—" : (100 * t.share_used).toFixed(1) + "%", t.refused].map((v) => el("td", {}, String(v)))));
  box.append(sec("Token service (OPRF queries)", tk));
  box.append(sec("Audit", el("p", {class: "muted"}, `${L.requests.length} evidence requests recorded; every one is listed in /api/ledger.`)));
}
$("#tabCases").onclick = () => { $("#cases").style.display = ""; $("#ledger").style.display = "none"; $("#tabCases").className = "on"; $("#tabLedger").className = ""; };
$("#tabLedger").onclick = () => { $("#cases").style.display = "none"; $("#ledger").style.display = "block"; $("#tabLedger").className = "on"; $("#tabCases").className = ""; showLedger(); };
init();
</script></body></html>
"""

__all__ = ["ACTIONS", "PAGE", "console_app", "queue"]
