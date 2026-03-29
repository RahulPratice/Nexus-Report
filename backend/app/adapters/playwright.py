from datetime import datetime
from app.adapters.base import BaseAdapter, register_adapter
from app.models.utrs import TestRun, TestResult, TestStep, TestStatus


@register_adapter("playwright")
class PlaywrightAdapter(BaseAdapter):
    """
    Parses Playwright's JSON reporter output.
    Compatible with: @playwright/test >= 1.20.0
    """

    def parse(self, raw: dict) -> TestRun:
        project_id = raw.get("_nexus_project_id", "")
        results: list[TestResult] = []

        for suite in raw.get("suites", []):
            results.extend(self._parse_suite(suite))

        run = TestRun(
            project_id=project_id,
            tool="playwright",
            tool_version=raw.get("version"),
            branch=raw.get("_nexus_branch"),
            commit_sha=raw.get("_nexus_commit"),
            environment=raw.get("_nexus_env"),
            ci_provider=raw.get("_nexus_ci"),
            ci_run_url=raw.get("_nexus_ci_url"),
            started_at=datetime.utcfromtimestamp(raw["startTime"] / 1000)
                       if raw.get("startTime") else datetime.utcnow(),
            duration_ms=raw.get("stats", {}).get("duration", 0),
            results=results,
        )
        return run.compute_aggregates()

    def _parse_suite(self, suite: dict, parent_title: str = "") -> list[TestResult]:
        results = []
        title = suite.get("title", "")
        full_suite = f"{parent_title} > {title}".strip(" > ")

        for spec in suite.get("specs", []):
            for test in spec.get("tests", []):
                result = self._parse_test(spec, test, full_suite)
                results.append(result)

        for child_suite in suite.get("suites", []):
            results.extend(self._parse_suite(child_suite, full_suite))

        return results

    def _parse_test(self, spec: dict, test: dict, suite: str) -> TestResult:
        test_results = test.get("results", [])
        last_result  = test_results[-1] if test_results else {}

        status_map = {
            "passed":    TestStatus.PASSED,
            "failed":    TestStatus.FAILED,
            "timedOut":  TestStatus.FAILED,
            "skipped":   TestStatus.SKIPPED,
            "interrupted": TestStatus.BROKEN,
        }

        raw_status = test.get("status", "unknown")
        # Detect flaky: multiple attempts with mixed results
        statuses = [r.get("status") for r in test_results]
        is_flaky = len(test_results) > 1 and "passed" in statuses and "failed" in statuses

        steps = [
            TestStep(
                name=step.get("title", ""),
                status=TestStatus.PASSED if step.get("error") is None else TestStatus.FAILED,
                duration_ms=step.get("duration", 0),
                error=step.get("error", {}).get("message") if step.get("error") else None,
            )
            for step in last_result.get("steps", [])
        ]

        error = last_result.get("error")

        return TestResult(
            name=spec.get("title", ""),
            suite=suite,
            file_path=spec.get("file"),
            status=TestStatus.FLAKY if is_flaky else status_map.get(raw_status, TestStatus.FAILED),
            duration_ms=last_result.get("duration", 0),
            error_message=error.get("message") if error else None,
            stack_trace=error.get("stack") if error else None,
            retry_count=len(test_results) - 1,
            browser=test.get("projectName"),
            steps=steps,
            screenshot_url=self._find_attachment(last_result, "screenshot"),
            video_url=self._find_attachment(last_result, "video"),
            trace_url=self._find_attachment(last_result, "trace"),
            tags=spec.get("tags", []),
        )

    def _find_attachment(self, result: dict, content_type: str) -> str | None:
        for att in result.get("attachments", []):
            if content_type in att.get("contentType", "").lower():
                return att.get("path") or att.get("body")
        return None
