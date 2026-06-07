from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class TestResult:
    test_id: str
    test_name: str
    class_name: Optional[str]
    outcome: str
    start_time: datetime
    end_time: datetime
    duration_ms: float
    computer_name: Optional[str]
    error_message: Optional[str]
    stack_trace: Optional[str]

    @property
    def display_name(self) -> str:
        if self.class_name:
            return f"{self.class_name}.{self.test_name}"
        return self.test_name


@dataclass
class TestRun:
    source_file: str
    run_start: datetime
    run_finish: datetime
    results: list[TestResult] = field(default_factory=list)

    @property
    def total_duration_s(self) -> float:
        return (self.run_finish - self.run_start).total_seconds()

    @property
    def counts(self) -> dict[str, int]:
        passed = failed = skipped = other = 0
        for r in self.results:
            o = r.outcome.lower()
            if o == "passed":
                passed += 1
            elif o == "failed":
                failed += 1
            elif o in ("notexecuted", "inconclusive", "pending"):
                skipped += 1
            else:
                other += 1
        return {
            "total": len(self.results),
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "other": other,
        }

    @property
    def failures(self) -> list[TestResult]:
        return [r for r in self.results if r.outcome.lower() == "failed"]
