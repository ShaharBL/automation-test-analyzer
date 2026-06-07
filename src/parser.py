from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .models import TestResult, TestRun

NS = {"t": "http://microsoft.com/schemas/VisualStudio/TeamTest/2010"}

_DURATION_RE = re.compile(r"^(\d+):(\d{2}):(\d{2})(?:\.(\d+))?$")


def _parse_iso(ts: str) -> datetime:
    # .NET often writes 7-digit fractional seconds; fromisoformat handles up to 6.
    ts = ts.strip()
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    # Trim fractional seconds to 6 digits if longer.
    m = re.match(r"^(.*\.\d{6})\d+(.*)$", ts)
    if m:
        ts = m.group(1) + m.group(2)
    return datetime.fromisoformat(ts)


def _parse_duration(s: Optional[str]) -> float:
    """Parse HH:MM:SS.fffffff into milliseconds."""
    if not s:
        return 0.0
    m = _DURATION_RE.match(s.strip())
    if not m:
        return 0.0
    h, mm, ss, frac = m.groups()
    total = int(h) * 3600 + int(mm) * 60 + int(ss)
    micro = 0
    if frac:
        # frac may be up to 7 digits; pad/truncate to 6 for microseconds.
        frac6 = (frac + "000000")[:6]
        micro = int(frac6)
    td = timedelta(seconds=total, microseconds=micro)
    return td.total_seconds() * 1000.0


def _build_method_index(root: ET.Element) -> dict[str, tuple[str, str]]:
    """Map testId -> (className, testName) via TestDefinitions."""
    idx: dict[str, tuple[str, str]] = {}
    defs = root.find("t:TestDefinitions", NS)
    if defs is None:
        return idx
    for ut in defs.findall("t:UnitTest", NS):
        test_id = ut.get("id") or ""
        method = ut.find("t:TestMethod", NS)
        if test_id and method is not None:
            class_name = method.get("className") or ""
            # Strip assembly suffix if className contains comma (e.g. "Ns.Cls, MyAssembly").
            if "," in class_name:
                class_name = class_name.split(",", 1)[0].strip()
            test_name = method.get("name") or ut.get("name") or ""
            idx[test_id] = (class_name, test_name)
    return idx


def _extract_error(unit_result: ET.Element) -> tuple[Optional[str], Optional[str]]:
    output = unit_result.find("t:Output", NS)
    if output is None:
        return None, None
    err = output.find("t:ErrorInfo", NS)
    if err is None:
        return None, None
    msg_el = err.find("t:Message", NS)
    trace_el = err.find("t:StackTrace", NS)
    msg = msg_el.text.strip() if msg_el is not None and msg_el.text else None
    trace = trace_el.text.strip() if trace_el is not None and trace_el.text else None
    return msg, trace


def parse_trx(path: Path) -> TestRun:
    tree = ET.parse(path)
    root = tree.getroot()

    times = root.find("t:Times", NS)
    run_start = _parse_iso(times.get("start")) if times is not None and times.get("start") else datetime.min
    run_finish = _parse_iso(times.get("finish")) if times is not None and times.get("finish") else run_start

    method_index = _build_method_index(root)

    results: list[TestResult] = []
    results_node = root.find("t:Results", NS)
    if results_node is not None:
        for r in results_node.findall("t:UnitTestResult", NS):
            test_id = r.get("testId") or ""
            test_name = r.get("testName") or "<unnamed>"
            class_name = None
            if test_id in method_index:
                cls, method_name = method_index[test_id]
                class_name = cls or None
                # Prefer method name from TestDefinitions if testName is empty.
                if not r.get("testName") and method_name:
                    test_name = method_name

            start = r.get("startTime")
            end = r.get("endTime")
            start_dt = _parse_iso(start) if start else run_start
            end_dt = _parse_iso(end) if end else start_dt

            duration_ms = _parse_duration(r.get("duration"))
            # Fall back to end-start if duration attr is missing.
            if duration_ms == 0.0 and end_dt > start_dt:
                duration_ms = (end_dt - start_dt).total_seconds() * 1000.0
            # Make sure end >= start for the timeline.
            if end_dt < start_dt:
                end_dt = start_dt + timedelta(milliseconds=duration_ms)

            err_msg, stack = _extract_error(r)

            results.append(
                TestResult(
                    test_id=test_id,
                    test_name=test_name,
                    class_name=class_name,
                    outcome=r.get("outcome") or "Unknown",
                    start_time=start_dt,
                    end_time=end_dt,
                    duration_ms=duration_ms,
                    computer_name=r.get("computerName"),
                    error_message=err_msg,
                    stack_trace=stack,
                )
            )

    # If we never got a run window, derive one from the results.
    if results and (run_start == datetime.min or run_finish == datetime.min):
        run_start = min(r.start_time for r in results)
        run_finish = max(r.end_time for r in results)

    return TestRun(
        source_file=path.name,
        run_start=run_start,
        run_finish=run_finish,
        results=results,
    )
