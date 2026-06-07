from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .models import TestRun

TEMPLATES_DIR = Path(__file__).parent / "templates"


def _normalize_outcome(outcome: str) -> str:
    o = (outcome or "").lower()
    if o == "passed":
        return "Passed"
    if o == "failed":
        return "Failed"
    if o in ("notexecuted", "inconclusive", "pending"):
        return "NotExecuted"
    if o in ("timeout", "aborted"):
        return "Aborted"
    if o == "error":
        return "Error"
    return outcome or "Unknown"


def _run_to_dict(run: TestRun, index: int) -> dict:
    sorted_results = sorted(run.results, key=lambda r: r.start_time)
    if sorted_results:
        anchor = min(run.run_start, sorted_results[0].start_time)
    else:
        anchor = run.run_start
    anchor_ms = int(anchor.timestamp() * 1000)

    tests = []
    outcome_dist: dict[str, int] = {}
    for i, r in enumerate(sorted_results):
        outcome = _normalize_outcome(r.outcome)
        outcome_dist[outcome] = outcome_dist.get(outcome, 0) + 1
        start_ms = int(r.start_time.timestamp() * 1000)
        end_ms = int(r.end_time.timestamp() * 1000)
        tests.append({
            "i": i,
            "name": r.display_name,
            "outcome": outcome,
            "raw_outcome": r.outcome,
            "rel_start_ms": start_ms - anchor_ms,
            "rel_end_ms": max(end_ms - anchor_ms, start_ms - anchor_ms + 1),
            "start_iso": r.start_time.isoformat(),
            "end_iso": r.end_time.isoformat(),
            "duration_ms": round(r.duration_ms, 2),
            "error_message": r.error_message or "",
            "stack_trace": r.stack_trace or "",
        })

    counts = run.counts
    total = counts["total"] or 0
    pass_rate = round(100.0 * counts["passed"] / total, 1) if total else 0.0

    return {
        "index": index,
        "source_file": run.source_file,
        "run_start": run.run_start.isoformat(),
        "run_finish": run.run_finish.isoformat(),
        "total_duration_s": round(run.total_duration_s, 2),
        "counts": counts,
        "outcome_dist": outcome_dist,
        "pass_rate": pass_rate,
        "tests": tests,
    }


def build_dashboard(runs: list[TestRun]) -> str:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("dashboard.html.j2")

    runs_data = [_run_to_dict(r, i) for i, r in enumerate(runs)]
    # Embed inside a <script type="application/json"> tag; the only sequence
    # we have to neutralise is a literal "</script" in user-supplied strings.
    runs_json = json.dumps(runs_data, ensure_ascii=False).replace("</", "<\\/")

    return template.render(runs=runs_data, runs_json=runs_json)
