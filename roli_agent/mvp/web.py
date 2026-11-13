"""Phase 3: the web interface (FastAPI + Jinja2; SPEC_3_mvp.md section 4).

    .venv/bin/uvicorn roli_agent.mvp.web:app --host 127.0.0.1 --port 8008            # local mode: Julius alone, loopback only, no token
    ROLI_WEB_TOKEN=<shared secret> .venv/bin/uvicorn roli_agent.mvp.web:app ...        # shared mode: every route needs the token (query once, then a cookie)

Local-testing milestone (2026-11-04): without ROLI_WEB_TOKEN the app runs in local mode and must only ever be bound to 127.0.0.1 (the launch
script does that); with a token set, the Phase 3 behaviour is unchanged. A run starts in a background thread; the run page refreshes itself until
done and shows progress and spending as it goes. Pages are rendered from the run's own JSON; no number on a page comes from anywhere else.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from jinja2 import DictLoader, Environment

from ..config import ROOT
from .menu_run import DEFAULT_RUNS, MenuRunner, load_run, prepare_photo
from .models import Feedback, MenuRun, MvpConfig

MAX_UPLOAD_BYTES = 12 * 1024 * 1024
COOKIE = "roli_token"

BASE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Roli (invited testers)</title>
<style>body{font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;max-width:900px;margin:24px auto;padding:0 16px;color:#222;line-height:1.45}
.banner{background:#fff4d6;border:1px solid #e0b640;padding:10px 14px;border-radius:6px;margin-bottom:18px;font-size:.95em}
.card{border:1px solid #ddd;border-radius:8px;padding:14px 16px;margin:12px 0}.muted{color:#666;font-size:.9em}table{border-collapse:collapse;width:100%;font-size:.9em}
td,th{border-bottom:1px solid #eee;padding:6px 8px;text-align:left;vertical-align:top}code{background:#f3f3f3;padding:1px 4px;border-radius:3px}
.tag{display:inline-block;padding:1px 7px;border-radius:10px;font-size:.8em;background:#eee}.ws{background:#d8f0d8}.te{background:#fff0c2}.cc{background:#ffe0cc}
details{margin:6px 0}summary{cursor:pointer}textarea,input[type=text]{width:100%}</style></head><body>
<div class="banner"><strong>Experimental.</strong> {{ banner }}{% if local_mode %} <span class="muted">Local mode: this Mac only, no sign-in.</span>{% endif %}</div>
<p class="muted"><a href="/?token={{ token }}">New menu</a> · <a href="/runs?token={{ token }}">Past runs</a></p>
{% block body %}{% endblock %}
</body></html>"""

INDEX = """{% extends "base" %}{% block body %}
<h1>Roli: which dish is lowest in saturated fat?</h1>
<p>Upload a photo of a restaurant menu. Roli reads it, picks up to {{ config.max_dishes }} dishes across the courses (sides, soups, dips, desserts and children's dishes are listed apart, never in the top three), looks up
published recipes for each, prices every ingredient against USDA FoodData Central, models a restaurant portion, and recommends up to three dishes with
the lowest saturated fat (cholesterol second). A run takes 2-8 minutes. Spending is capped at ${{ config.menu_budget_usd }} of model calls and
{{ config.menu_search_credits }} search credits per menu.</p>
<form class="card" method="post" action="/menu?token={{ token }}" enctype="multipart/form-data">
<p><input type="file" name="photo" accept="image/*" required></p>
<p><label>Restaurant name (optional) <input type="text" name="restaurant" maxlength="120"></label></p>
<p><button type="submit">Read this menu</button></p></form>
{% endblock %}"""

RUN = """{% extends "base" %}{% block body %}
{% if run.status == "running" %}<meta http-equiv="refresh" content="5">
<h1>Working on your menu…</h1><p class="muted">This page refreshes every 5 seconds. {{ progress|length }} steps so far.</p>
<ul>{% for p in progress|reverse %}<li class="muted">{{ p }}</li>{% endfor %}</ul>
{% else %}
<h1>Recommendation</h1>
<div class="card"><p style="font-size:1.1em">{{ run.recommendation }}</p><p class="muted">{{ run.recommendation_words }} words · run {{ run.run_id }}
{% if run.spend %} · model calls ${{ run.spend.model_usd_total[:6] }} ({{ run.spend.model_calls }} calls{% if run.spend.model_usd_estimated != "0.000000" %}, ${{ run.spend.model_usd_estimated[:6] }} of it estimated{% endif %}) · {{ run.spend.search_credits }} search credits{% endif %}</p>
{% if run.spend and run.spend.interruptions %}<p><strong>Budget stop:</strong> {{ run.spend.interruptions|join("; ") }}</p>{% endif %}
{% if run.usda %}<p class="muted">USDA FoodData Central: {{ run.usda.requests }} requests this run{% if run.usda.remaining_after is not none %}, {{ run.usda.remaining_after }} of {{ run.usda.limit }} left this hour{% endif %}{% if run.usda.halted %} · <strong>USDA refused requests this hour; nothing more is asked until it passes</strong>{% endif %}{% if run.usda.release %} · data release: {% for t, r in run.usda.release.items() %}{{ t }} {{ r.latest_publication_date }}{% if r.pending_publication_date %} (newer {{ r.pending_publication_date }} published, awaiting approval){% endif %}{% if not loop.last %}, {% endif %}{% endfor %}{% endif %}</p>{% endif %}</div>
{% if run.ranking %}<h2>All ranked dishes</h2><p class="muted">Ordered by the middle of each dish's band ("most plates": the 10th-90th percentile of simulated plates; the extremes beside it are the outer limits); a practical ranking value, not a verified figure; cholesterol breaks a near tie.</p>
<table><tr><th>#</th><th>Dish</th><th>Saturated fat / plate (most plates · extremes · middle)</th><th>Cholesterol / plate</th><th>Support</th></tr>
{% for r in run.ranking %}<tr><td>{{ "" if (r.listed_apart or r.snack) else r.rank }}</td><td>{{ r.name }}{% if r.listed_apart or r.snack %} <span class="muted">({{ r.listed_apart or "snack" }}, listed apart: never in the top three)</span>{% endif %}{% if r.fat_line %}<br><span class="muted">{{ r.fat_line }}</span>{% endif %}</td><td>{% if r.band_low is not none %}<strong>{{ "%.1f"|format(r.band_low|float) }}–{{ "%.1f"|format(r.band_high|float) }} g</strong> · {% endif %}{{ "%.1f"|format(r.saturated_fat_low|float) }}–{{ "%.1f"|format(r.saturated_fat_high|float) }} g{% if r.saturated_fat_mid is not none %} · {{ "%.1f"|format(r.saturated_fat_mid|float) }} g{% endif %}{% if r.set_aside %} <span class="muted">({{ r.set_aside|length }} recipe set aside)</span>{% endif %}{% if r.tie_broken_by_cholesterol %} <span class="muted">(tie on saturated fat; cholesterol decided)</span>{% endif %}</td>
<td>{% if r.cholesterol_band_low is not none %}<strong>{{ "%.0f"|format(r.cholesterol_band_low|float) }}–{{ "%.0f"|format(r.cholesterol_band_high|float) }} mg</strong> · {% endif %}{% if r.cholesterol_high is not none %}{{ "%.0f"|format(r.cholesterol_low|float) }}–{{ "%.0f"|format(r.cholesterol_high|float) }} mg{% else %}no upper bound{% endif %}</td>
<td><span class="tag {{ {'well_supported':'ws','tentative':'te','close_call':'cc'}.get(r.support,'') }}">{{ r.support.replace('_',' ') }}</span></td></tr>{% endfor %}</table>{% endif %}
{% if run.unranked %}<h3>Could not be ranked</h3><ul>{% for u in run.unranked %}<li>{{ u.name }}: <span class="muted">{{ u.reason }}</span>{% if u.fat_line %}<br>{{ u.fat_line }}{% endif %}</li>{% endfor %}</ul>{% endif %}
{% set flagged = run.dishes|selectattr("status","equalto","flagged")|rejectattr("reference.known_limit")|list %}
{% if flagged %}<p class="muted">Flagged dishes are left out until the cause is fixed; the diagnostics show Roli's figure beside the published range.</p>{% endif %}
{% set stopped = run.dishes|selectattr("status","equalto","budget_stopped")|list %}
{% if stopped %}<h3>Stopped by the spending limit</h3><ul>{% for d in stopped %}<li>{{ d.item.name }}: <span class="muted">{{ d.reason }}</span></li>{% endfor %}</ul>{% endif %}
{% set skipped = run.dishes|selectattr("status","equalto","skipped")|list %}
{% if skipped %}<details><summary>{{ skipped|length }} dishes not tried (cap or budget)</summary><ul>{% for d in skipped %}<li>{{ d.item.name }} <span class="muted">({{ d.reason }})</span></li>{% endfor %}</ul></details>{% endif %}
{% set excluded = run.dishes|rejectattr("status","in",["evaluated","no_recipes","error","skipped","budget_stopped"])|list %}
{% if excluded %}<details><summary>{{ excluded|length }} menu items outside what Roli ranks</summary><ul>{% for d in excluded %}<li>{{ d.item.name }} <span class="muted">({{ d.reason }})</span></li>{% endfor %}</ul></details>{% endif %}
<p><a href="/run/{{ run.run_id }}/diagnostics?token={{ token }}">Internal diagnostics</a> · {{ run.timings.get('total') }} s</p>
<h2>Tell us what looks wrong</h2>
<form class="card" method="post" action="/run/{{ run.run_id }}/feedback?token={{ token }}">
<p><label>Dish (optional) <select name="dish"><option value="">— whole menu —</option>{% for d in run.dishes %}<option value="{{ d.key }}">{{ d.item.name }}</option>{% endfor %}</select></label></p>
<p><label><input type="radio" name="kind" value="dish_inaccurate" required> A dish estimate looks wrong</label><br>
<label><input type="radio" name="kind" value="ranking_unexpected"> The ranking surprised me</label><br>
<label><input type="radio" name="kind" value="uncertainty_unhelpful"> The uncertainty wording did not help</label><br>
<label><input type="radio" name="kind" value="other"> Something else</label></p>
<p><textarea name="text" rows="3" maxlength="2000" placeholder="What did you expect, and why?"></textarea></p>
<p><button type="submit">Send feedback</button></p></form>
{% if saved %}<p class="muted">Thank you, your feedback was saved.</p>{% endif %}
{% endif %}{% endblock %}"""

DIAG = """{% extends "base" %}{% block body %}
<h1>Diagnostics: run {{ run.run_id }}</h1>
<p class="muted">{{ run.created_at }} · status {{ run.status }} · timings {{ run.timings }} · totals {{ run.totals }}</p>
{% if run.spend %}<div class="card"><strong>Spending</strong> · model calls ${{ run.spend.model_usd_total }} (actual ${{ run.spend.model_usd_actual }}, estimated ${{ run.spend.model_usd_estimated }}; {{ run.spend.model_calls }} calls: {{ run.spend.model_calls_priced_by_provider }} priced by the provider, {{ run.spend.model_calls_estimated_from_tokens }} estimated from tokens, {{ run.spend.model_calls_unpriced_flat_reserve }} flat reserve; prices: {{ run.spend.price_source }}) · {{ run.spend.search_credits }} search credits · limits {{ run.spend.limits }} · today before this run {{ run.spend.daily_before_this_run }} · after {{ run.spend.daily_after_this_run }}
{% if run.spend.interruptions %}<br><strong>Interruptions:</strong> {{ run.spend.interruptions|join("; ") }}{% endif %}</div>{% endif %}
<details><summary>Dish selection ({{ run.dishes|length }} menu items)</summary><table><tr><th>#</th><th>item</th><th>type</th><th>course</th><th>lean score</th><th>decision</th><th>why</th></tr>
{% for d in run.dishes %}<tr><td>{{ d.menu_index }}</td><td>{{ d.item.name }}</td><td>{{ d.dish_type or "" }}</td><td>{{ d.selection.get("course") or "" }}</td><td>{{ d.selection.get("lean_score") if d.selection else "" }}</td><td>{{ d.status }}</td><td class="muted">{{ d.selection.get("reason") or d.reason or "" }}</td></tr>{% endfor %}</table></details>
{% if run.errors %}<div class="card"><strong>Errors</strong><ul>{% for e in run.errors %}<li>{{ e }}</li>{% endfor %}</ul></div>{% endif %}
{% if run.usda %}<div class="card"><strong>USDA</strong> · {{ run.usda }}</div>{% endif %}
{% if run.flags %}<div class="card"><strong>Flags</strong><ul>{% for f in run.flags %}<li>{{ f.status }}: {{ f.dish }} ({{ f.card }}{% if f.status == "open" %}, {{ f.comparison }}; Roli {{ f.roli_middle }} vs published {{ f.published_low }}–{{ f.published_high }}; top: {% for t in f.top_contributors %}{{ t.line }} {{ t.sat_fat_g }} g{% if not loop.last %}, {% endif %}{% endfor %}{% else %}; {{ f.note }}{% endif %})</li>{% endfor %}</ul></div>{% endif %}
<h2>Ranking and reasons</h2>
{% for r in run.ranking %}<div class="card"><strong>{{ r.rank }}. {{ r.name }}</strong> <span class="tag">{{ r.support }}</span> · sat {{ r.saturated_fat_low }}–{{ r.saturated_fat_high }} g · chol {{ r.cholesterol_low }}–{{ r.cholesterol_high }} mg
<br>beats well supported {{ r.beats_well_supported }}, tentatively {{ r.beats_tentative }}, overlaps {{ r.overlaps }}
<ul>{% for x in r.reasons %}<li>{{ x }}</li>{% endfor %}</ul><p class="muted">caveats: {{ r.caveats|join(" / ") }}</p><p class="muted">drivers: {{ r.drivers|join(" | ") }}</p></div>{% endfor %}
{% if run.comparison %}<details><summary>Pairwise verdicts ({{ run.comparison.pairwise|length }})</summary><table><tr><th>nutrient</th><th>A</th><th>B</th><th>verdict</th><th>lower</th><th>reason</th></tr>
{% for p in run.comparison.pairwise %}<tr><td>{{ p.nutrient }}</td><td>{{ p.dish_a }}</td><td>{{ p.dish_b }}</td><td>{{ p.verdict }}</td><td>{{ p.lower }}</td><td>{{ p.reason }}{% if p.tentative_because %} <em>{{ p.tentative_because|join("; ") }}</em>{% endif %}</td></tr>{% endfor %}</table></details>{% endif %}
<h2>Dishes</h2>
{% for d in run.dishes %}<div class="card"><strong>{{ d.item.name }}</strong> <span class="muted">[{{ d.item.section }}] {{ d.item.description }}</span> · {{ d.status }} · type {{ d.dish_type }} · {{ d.seconds }} s
{% if d.reason %}<p class="muted">{{ d.reason }}</p>{% endif %}
{% if d.reference %}<p><strong>Reference check</strong> ({{ d.reference.card_id or "no card" }}){% if not d.reference.comparisons %}: <span class="muted">{{ d.reference.reason_unchecked }}</span>{% else %}: {% if d.reference.flagged %}<strong>flagged</strong>{% elif d.reference.below_published %}below the published range for this kind of dish; plain recipe (12.18: not flagged, ranked){% elif d.reference.checked %}inside the published range{% else %}shown only, nothing here may flag{% endif %}
{% for c in d.reference.comparisons %}<br><span class="muted">{{ c.basis }}{% if c.choice %} ({{ c.choice }}: {{ c.choice_basis|join("; ") }}){% endif %}: Roli's middle {{ c.roli_middle }} vs published {{ c.published_low }}–{{ c.published_high }}, {{ c.independent_figures }} independent figure(s){% if c.checked %}, allowed {{ c.allowed_low }}–{{ c.allowed_high }} at x{{ d.reference.factor }}{% if c.failed %} → {{ c.direction }}{% endif %}{% endif %}{% if c.note %} · {{ c.note }}{% endif %}</span>{% endfor %}
{% if d.reference.served_mass_low is not none %}<br><span class="muted">served mass {{ d.reference.served_mass_low }}–{{ d.reference.served_mass_high }} g</span>{% endif %}
{% if d.reference.top_contributors %}<br><span class="muted">top contributors: {% for t in d.reference.top_contributors %}{{ t.line }} {{ t.sat_fat_g }} g ({{ t.share_of_middle }}){% if not loop.last %}; {% endif %}{% endfor %}</span>{% endif %}{% endif %}</p>{% endif %}
{% if d.estimate %}
<p class="muted">cost: {{ d.cost }}</p>
{% for n, iv in d.intervals.items() %}<p><strong>{{ n }}</strong>: extremes {{ iv.low }}–{{ iv.high }} per portion ({{ iv.n_bounded }} of {{ iv.n_scenarios }} recipes bounded){% if iv.band_low is not none %}<br><strong>most plates {{ iv.band_low }}–{{ iv.band_high }}</strong>, middle {{ iv.band_mid }} ({{ iv.band_draws }} draws; plate weights: {{ iv.plate_source }}){% if iv.recipe_weights %}; recipe weights {{ iv.recipe_weights }}{% endif %}{% if iv.set_aside %}; set aside: {{ iv.set_aside|join(", ") }}{% endif %}{% endif %}<br><span class="muted">{{ iv.caveats|join(" / ") }}</span></p>{% endfor %}
<details><summary>{{ d.estimate.scenarios|length }} recipes read ({{ d.n_scenarios }} calculated, {{ d.n_portioned }} portioned)</summary>
{% for s in d.estimate.scenarios %}<div style="margin:8px 0 8px 12px"><a href="{{ s.source.url }}" rel="noopener">{{ s.source.title }}</a> <span class="muted">({{ s.source.host }}, yield "{{ s.source.yield_text }}", {{ s.status }}{% if s.status_reason %}: {{ s.status_reason }}{% endif %}, relevance {{ s.relevance.grade }}, basis {{ s.basis }})</span>
{% if s.status == "calculated" %}<table><tr><th>line</th><th>USDA record</th><th>g</th><th>state</th><th>blocker</th></tr>
{% for l in s.ingredients %}<tr><td>{{ l.line or ("menu-only: " ~ l.name) }}</td><td>{% if l.match and l.match.fdc_id %}{{ l.match.description }} ({{ l.match.fdc_id }}, {{ l.match.data_type }}{% if l.match.match_type == "proxy" %}, proxy{% endif %}){% else %}—{% endif %}</td>
<td>{{ l.conversion.grams if l.conversion.grams is not none else "?" }}</td><td>{{ l.preparation_state }}</td><td>{{ l.blocker or l.excluded_from_calculation or "" }}{% if l.tag_role %}<br><span class="muted">tag: {{ l.tag_role }} / {{ l.tag_kind }}{% if l.tag_note %} ({{ l.tag_note }}){% endif %}</span>{% endif %}</td></tr>{% endfor %}</table>
{% if s.inferences %}<p class="muted">inferences: {% for i in s.inferences %}{{ i.kind }} {{ i.name }} ({{ i.rule_id or "D20" }}); {% endfor %}</p>{% endif %}{% endif %}</div>{% endfor %}</details>
<details><summary>Assumptions ({{ d.estimate.adapted_pairs|length }} adapted pairs, mode {{ d.estimate.adapt_mode }})</summary>
{% for p in d.estimate.adapted_pairs %}<p><em>{{ p.derived_from }}</em> low {{ p.low.calculation_status }} / high {{ p.high.calculation_status }}</p><table><tr><th>line</th><th>gap</th><th>row</th><th>g low–high</th><th>basis</th><th>status</th></tr>
{% for a in p.assumptions %}<tr><td>{{ a.name }}</td><td>{{ a.gap }}</td><td>{{ a.row_id or a.source }}</td><td>{{ a.grams_low }}–{{ a.grams_high }} ({{ a.amount_basis }})</td><td>{{ a.basis[:140] }}</td><td>{{ a.review_status }}</td></tr>{% endfor %}
{% for u in p.unfilled %}<tr><td>{{ u.name }}</td><td colspan="4" class="muted">unfilled: {{ u.reason }}</td></tr>{% endfor %}</table>{% endfor %}</details>
{% if d.survey_dish %}<details><summary>USDA Survey fried-food record ({{ "applicable" if d.survey_dish.applicable else "not applicable" }})</summary>
<p class="muted">{{ d.survey_dish.reason or "" }} {% if d.survey_dish.applicable %}sat {{ d.survey_dish.totals.saturated_fat_g.low[:6] }}–{{ d.survey_dish.totals.saturated_fat_g.high[:6] }} g, chol {{ d.survey_dish.totals.cholesterol_mg.low[:6] }}–{{ d.survey_dish.totals.cholesterol_mg.high[:6] }} mg per plate{% endif %}</p>
<table><tr><th>component</th><th>USDA record</th><th>plate g</th><th>amount basis</th><th>USDA frying fat / 100 g</th><th>inputs</th><th>problem</th></tr>
{% for c in d.survey_dish.components %}<tr><td>{{ c.text }}</td><td>{{ c.description }} ({{ c.fdc_id }})<br><span class="muted">{{ c.choice }}</span></td><td>{{ c.grams_low }}–{{ c.grams_high }}</td><td class="muted">{{ c.amount_basis }}</td><td>{{ c.oil_g_per_100g }}</td><td class="muted">{{ c.inputs|join("; ") }}</td><td>{{ c.problem or "" }}</td></tr>{% endfor %}
{% for a in d.survey_dish.additions %}<tr><td>{{ a.name }}</td><td>{{ a.description }} ({{ a.fdc_id }}, row {{ a.row_id }})</td><td>{{ a.grams_low }}–{{ a.grams_high }}</td><td class="muted">weights row, per plate</td><td></td><td></td><td></td></tr>{% endfor %}</table>
{% if d.survey_dish.choice_ranges %}<p class="muted">{{ d.survey_dish.fat_note }}<br>{% for label, r in d.survey_dish.choice_ranges.items() %}{{ label }}: {{ r.saturated_fat_g.low[:5] }}–{{ r.saturated_fat_g.high[:5] }} g saturated fat per plate{% if not loop.last %}; {% endif %}{% endfor %}</p>{% endif %}
{% if d.survey_dish.uncovered %}<p class="muted">not covered: {{ d.survey_dish.uncovered|join(", ") }}</p>{% endif %}<p class="muted">{{ d.survey_dish.limitations|join(" / ") }}</p></details>{% endif %}
<details><summary>Portion models ({{ d.estimate.portioned|length }})</summary><table><tr><th>input</th><th>model / rule</th><th>f low–high</th><th>sat / portion</th><th>chol / portion</th><th>status / reason</th></tr>
{% for ps in d.estimate.portioned %}<tr><td>{{ ps.derived_from }} ({{ ps.input_kind }})</td><td>{{ ps.model }} {{ ps.portion_rule_id or "" }} <span class="muted">{{ ps.review_status }}</span></td>
<td>{% if ps.applicable %}{{ "%.3f"|format(ps.fraction_low.fraction|float) }}–{{ "%.3f"|format(ps.fraction_high.fraction|float) }}<br><span class="muted">{{ ps.fraction_high.arithmetic }}</span>{% endif %}</td>
<td>{% if ps.applicable %}{{ ps.low.per_portion.saturated_fat_g.known_subtotal }}–{{ ps.high.per_portion.saturated_fat_g.known_subtotal }}{% endif %}</td>
<td>{% if ps.applicable %}{{ ps.low.per_portion.cholesterol_mg.known_subtotal }}–{{ ps.high.per_portion.cholesterol_mg.known_subtotal }}{% endif %}</td>
<td>{% if ps.applicable %}{{ ps.limitations|join(" / ") }}{% else %}{{ ps.not_applicable_reason }}{% endif %}</td></tr>{% endfor %}</table></details>
{% endif %}</div>{% endfor %}
<p><a href="/run/{{ run.run_id }}/json?token={{ token }}">Raw JSON</a></p>
{% endblock %}"""

RUNS = """{% extends "base" %}{% block body %}<h1>Past runs</h1><table><tr><th>run</th><th>created</th><th>status</th><th>ranked</th><th>recommendation</th></tr>
{% for r in runs %}<tr><td><a href="/run/{{ r.run_id }}?token={{ token }}">{{ r.run_id }}</a></td><td>{{ r.created_at }}</td><td>{{ r.status }}</td><td>{{ r.ranking|length }}</td><td>{{ r.recommendation[:160] }}</td></tr>{% endfor %}</table>{% endblock %}"""

ENV = Environment(loader=DictLoader({"base": BASE, "index": INDEX, "run": RUN, "diag": DIAG, "runs": RUNS}), autoescape=True)   # 12.12.8: every page; the templates' names have no .html, so select_autoescape(["html"]) escaped nothing


class RunStore:
    """Runs in flight (progress lines, the runner thread) and finished runs on disk."""

    def __init__(self, runs_dir: Path) -> None:
        self.runs_dir = Path(runs_dir)
        self.live: dict[str, dict[str, Any]] = {}
        self.lock = threading.Lock()

    def start(self, runner: MenuRunner, run_id: str, photo: Path) -> None:
        state = {"progress": [], "run": None}
        with self.lock:
            self.live[run_id] = state

        def say(msg: str) -> None:
            with self.lock:
                state["progress"].append(f"{datetime.now(timezone.utc).strftime('%H:%M:%S')} {msg}")

        def go() -> None:
            try:
                state["run"] = runner.run(photo, run_id=run_id, progress=say)
            except Exception as exc:                        # noqa: BLE001
                say(f"run failed: {type(exc).__name__}: {str(exc)[:200]}")
                failed = MenuRun(run_id=run_id, created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"), config=runner.config, photo=str(photo),
                                 status="failed", errors=[f"{type(exc).__name__}: {str(exc)[:200]}"], recommendation="Roli could not finish this menu; please try again.", recommendation_words=9)
                runner.save(failed)
                state["run"] = failed
        threading.Thread(target=go, daemon=True).start()

    def get(self, run_id: str) -> tuple[MenuRun | None, list[str]]:
        with self.lock:
            state = self.live.get(run_id)
        if state is not None:
            if state["run"] is not None:
                return state["run"], list(state["progress"])
            return MenuRun(run_id=run_id, created_at="", config=MvpConfig(), status="running"), list(state["progress"])
        return load_run(self.runs_dir, run_id), []

    def list(self) -> list[MenuRun]:
        out = []
        if self.runs_dir.exists():
            for folder in sorted(self.runs_dir.iterdir(), reverse=True):
                r = load_run(self.runs_dir, folder.name)
                if r is not None:
                    out.append(r)
        return out[:50]


def create_app(runner: MenuRunner | None = None, *, token: str | None = None, runs_dir: Path = DEFAULT_RUNS, local: bool | None = None) -> FastAPI:
    """`token` empty and `local` not False -> local mode (no token check; bind to 127.0.0.1 only). A token makes every route require it."""
    token = token if token is not None else os.environ.get("ROLI_WEB_TOKEN", "")
    local_mode = (not token) if local is None else local
    if not token and not local_mode:
        raise RuntimeError("ROLI_WEB_TOKEN is not set: the prototype is private and needs a shared token (or local mode)")
    app = FastAPI(title="Roli (local prototype)" if local_mode else "Roli (invited testers)", docs_url=None, redoc_url=None, openapi_url=None)
    store = RunStore(runs_dir)
    state: dict[str, Any] = {"runner": runner}

    def get_runner() -> MenuRunner:
        if state["runner"] is None:
            state["runner"] = MenuRunner(MvpConfig(), runs_dir=runs_dir)
        return state["runner"]

    def check(request: Request) -> str:
        if local_mode:
            return ""
        given = request.query_params.get("token") or request.cookies.get(COOKIE) or ""
        if given != token:
            raise HTTPException(status_code=401, detail="This prototype is private. Open the link you were given.")
        return given

    def render(name: str, request: Request, **ctx) -> HTMLResponse:
        cfg = get_runner().config if state["runner"] else MvpConfig()
        html = ENV.get_template(name).render(token=token, local_mode=local_mode, banner=cfg.banner, config=cfg, **ctx)
        resp = HTMLResponse(html)
        if token:
            resp.set_cookie(COOKIE, token, httponly=True, samesite="lax", max_age=30 * 24 * 3600)
        return resp

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request):
        check(request)
        return render("index", request)

    @app.post("/menu")
    async def start_menu(request: Request, photo: UploadFile = File(...), restaurant: str = Form("")):
        check(request)
        data = await photo.read()
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="The photo is larger than 12 MB.")
        run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-") + os.urandom(3).hex()
        folder = Path(runs_dir) / run_id
        try:
            path = prepare_photo(data, folder / "menu.jpg")
        except Exception:                                   # noqa: BLE001  not an image
            raise HTTPException(status_code=400, detail="That file is not an image Roli can read.")
        if restaurant.strip():
            (folder / "restaurant.txt").write_text(restaurant.strip()[:120], encoding="utf-8")
        store.start(get_runner(), run_id, path)
        return RedirectResponse(url=f"/run/{run_id}?token={token}", status_code=303)

    @app.get("/run/{run_id}", response_class=HTMLResponse)
    def show_run(request: Request, run_id: str, saved: int = 0):
        check(request)
        run, progress = store.get(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="No such run.")
        return render("run", request, run=run, progress=progress, saved=bool(saved))

    @app.get("/run/{run_id}/diagnostics", response_class=HTMLResponse)
    def diagnostics(request: Request, run_id: str):
        check(request)
        run, _ = store.get(run_id)
        if run is None or run.status == "running":
            raise HTTPException(status_code=404, detail="No finished run with that id.")
        return render("diag", request, run=run)

    @app.get("/run/{run_id}/json")
    def run_json(request: Request, run_id: str):
        check(request)
        run, _ = store.get(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="No such run.")
        return JSONResponse(json.loads(run.model_dump_json()))

    @app.post("/run/{run_id}/feedback")
    def feedback(request: Request, run_id: str, kind: str = Form(...), dish: str = Form(""), text: str = Form("")):
        check(request)
        run, _ = store.get(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="No such run.")
        try:
            fb = Feedback(run_id=run_id, dish=dish or None, kind=kind, text=text.strip()[:2000], submitted_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
        except Exception:                                   # noqa: BLE001
            raise HTTPException(status_code=400, detail="Unknown feedback kind.")
        path = Path(runs_dir) / "feedback.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(fb.model_dump_json() + "\n")
        return RedirectResponse(url=f"/run/{run_id}?token={token}&saved=1", status_code=303)

    @app.get("/runs", response_class=HTMLResponse)
    def runs(request: Request):
        check(request)
        return render("runs", request, runs=store.list())

    return app


def _lazy_app():
    """`uvicorn roli_agent.mvp.web:app` builds the app on import with the real runner and the token from .env."""
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    return create_app()


try:
    app = _lazy_app()
except Exception:                                           # noqa: BLE001  tests build their own app; a missing .env key shows up when a run starts
    app = None
