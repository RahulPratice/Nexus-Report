"""
Cypress adapter — parses Cypress Mochawesome JSON output
Compatible with: mochawesome-reporter >= 6.0.0
"""
from datetime import datetime
from app.adapters.base import BaseAdapter, register_adapter
from app.models.utrs import TestRun, TestResult, TestStatus


@register_adapter("cypress")
class CypressAdapter(BaseAdapter):

    def parse(self, raw: dict) -> TestRun:
        project_id = raw.get("_nexus_project_id", "")
        stats = raw.get("stats", {})
        results = []

        for suite in raw.get("results", []):
            results.extend(self._parse_suite(suite))

        started = stats.get("start")
        run = TestRun(
            project_id=project_id,
            tool="cypress",
            branch=raw.get("_nexus_branch"),
            commit_sha=raw.get("_nexus_commit"),
            environment=raw.get("_nexus_env"),
            started_at=datetime.fromisoformat(started.replace("Z", "+00:00"))
                       if started else datetime.utcnow(),
            duration_ms=stats.get("duration", 0),
            results=results,
        )
        return run.compute_aggregates()

    def _parse_suite(self, suite: dict, parent: str = "") -> list[TestResult]:
        results = []
        title = f"{parent} > {suite.get('title', '')}".strip(" > ")

        for test in suite.get("tests", []):
            status_map = {"passing": TestStatus.PASSED, "failing": TestStatus.FAILED, "pending": TestStatus.SKIPPED}
            err = test.get("err", {})
            results.append(TestResult(
                name=test.get("title", ""),
                suite=title,
                file_path=suite.get("file"),
                status=status_map.get(test.get("state", ""), TestStatus.FAILED),
                duration_ms=test.get("duration", 0),
                error_message=err.get("message") if err else None,
                stack_trace=err.get("estack") if err else None,
                retry_count=test.get("attempts", 0),
            ))

        for child in suite.get("suites", []):
            results.extend(self._parse_suite(child, title))
        return results
