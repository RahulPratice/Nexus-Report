from datetime import datetime
from app.adapters.base import BaseAdapter, register_adapter
from app.models.utrs import TestRun, TestResult, TestStatus


# ─── Jest / Vitest ────────────────────────────────────────────────────────────
@register_adapter("jest")
@register_adapter("vitest")
class JestAdapter(BaseAdapter):
    """Parses Jest --json reporter output. Also compatible with Vitest."""

    def parse(self, raw: dict) -> TestRun:
        project_id = raw.get("_nexus_project_id", "")
        results = []

        for test_file in raw.get("testResults", []):
            suite_name = test_file.get("testFilePath", "").split("/")[-1]
            for test in test_file.get("testResults", []):
                ancestor = " > ".join(test.get("ancestorTitles", []))
                suite    = f"{suite_name} > {ancestor}".strip(" > ")
                status_map = {
                    "passed":  TestStatus.PASSED,
                    "failed":  TestStatus.FAILED,
                    "pending": TestStatus.SKIPPED,
                    "todo":    TestStatus.SKIPPED,
                }
                results.append(TestResult(
                    name=test.get("title", ""),
                    suite=suite,
                    file_path=test_file.get("testFilePath"),
                    status=status_map.get(test.get("status", ""), TestStatus.FAILED),
                    duration_ms=test.get("duration", 0),
                    error_message="\n".join(test.get("failureMessages", [])) or None,
                    tags=test.get("tags", []),
                ))

        run = TestRun(
            project_id=project_id,
            tool="jest",
            branch=raw.get("_nexus_branch"),
            commit_sha=raw.get("_nexus_commit"),
            started_at=datetime.utcfromtimestamp(raw["startTime"] / 1000)
                       if raw.get("startTime") else datetime.utcnow(),
            duration_ms=raw.get("testResults", [{}])[-1].get("perfStats", {}).get("end", 0) -
                        raw.get("testResults", [{}])[0].get("perfStats", {}).get("start", 0)
                        if raw.get("testResults") else 0,
            results=results,
        )
        return run.compute_aggregates()


# ─── k6 (Performance) ─────────────────────────────────────────────────────────
@register_adapter("k6")
class K6Adapter(BaseAdapter):
    """
    Parses k6 --summary-export JSON output.
    Maps k6 thresholds to pass/fail test results.
    Also ingests custom metrics as individual test cases.
    """

    def parse(self, raw: dict) -> TestRun:
        project_id = raw.get("_nexus_project_id", "")
        metrics    = raw.get("metrics", {})
        results    = []

        for metric_name, data in metrics.items():
            thresholds = data.get("thresholds", {})
            if not thresholds:
                continue
            all_pass = all(thresholds.values())
            values   = data.get("values", {})
            results.append(TestResult(
                name=metric_name,
                suite="performance",
                status=TestStatus.PASSED if all_pass else TestStatus.FAILED,
                duration_ms=0,
                error_message=None if all_pass else f"Threshold not met: {thresholds}",
                metadata={
                    "avg": values.get("avg"),
                    "min": values.get("min"),
                    "max": values.get("max"),
                    "p90": values.get("p(90)"),
                    "p95": values.get("p(95)"),
                    "p99": values.get("p(99)"),
                    "rate": values.get("rate"),
                    "count": values.get("count"),
                },
            ))

        run = TestRun(
            project_id=project_id,
            tool="k6",
            branch=raw.get("_nexus_branch"),
            environment=raw.get("_nexus_env"),
            started_at=datetime.utcnow(),
            results=results,
            metadata={"scenario": raw.get("_nexus_scenario", "default")},
        )
        return run.compute_aggregates()


# ─── Postman / Newman ─────────────────────────────────────────────────────────
@register_adapter("postman")
@register_adapter("newman")
class PostmanAdapter(BaseAdapter):
    """
    Parses Newman JSON reporter output.
    Compatible with: newman >= 5.0.0 with --reporters json
    """

    def parse(self, raw: dict) -> TestRun:
        project_id = raw.get("_nexus_project_id", "")
        results    = []

        collection = raw.get("collection", {})
        run        = raw.get("run", {})

        for execution in run.get("executions", []):
            item       = execution.get("item", {})
            suite_name = collection.get("info", {}).get("name", "API Collection")

            for assertion in execution.get("assertions", []):
                err = assertion.get("error")
                results.append(TestResult(
                    name=assertion.get("assertion", ""),
                    suite=f"{suite_name} > {item.get('name', '')}",
                    status=TestStatus.FAILED if err else TestStatus.PASSED,
                    duration_ms=execution.get("response", {}).get("responseTime", 0),
                    error_message=err.get("message") if err else None,
                    metadata={
                        "method": execution.get("request", {}).get("method"),
                        "url": str(execution.get("request", {}).get("url", "")),
                        "status_code": execution.get("response", {}).get("code"),
                    },
                ))

        started = run.get("timings", {}).get("started")
        run_obj = TestRun(
            project_id=project_id,
            tool="postman",
            branch=raw.get("_nexus_branch"),
            environment=raw.get("_nexus_env"),
            started_at=datetime.utcfromtimestamp(started / 1000)
                       if started else datetime.utcnow(),
            duration_ms=run.get("timings", {}).get("completed", 0) - (started or 0),
            results=results,
        )
        return run_obj.compute_aggregates()


# ─── Selenium / WebdriverIO ───────────────────────────────────────────────────
@register_adapter("selenium")
@register_adapter("webdriverio")
class SeleniumAdapter(BaseAdapter):
    """
    Parses Selenium/WebdriverIO JUnit XML (converted to JSON) or WDIO JSON reporter.
    Send your test results converted from JUnit XML to JSON.
    """

    def parse(self, raw: dict) -> TestRun:
        project_id = raw.get("_nexus_project_id", "")
        results    = []

        for suite in raw.get("testsuites", {}).get("testsuite", []):
            suite_name = suite.get("@name", "")
            for test in suite.get("testcase", []):
                failure = test.get("failure")
                error   = test.get("error")
                skipped = "skipped" in test

                if skipped:
                    status = TestStatus.SKIPPED
                elif failure or error:
                    status = TestStatus.FAILED
                else:
                    status = TestStatus.PASSED

                err_msg = None
                stack   = None
                if failure:
                    err_msg = failure.get("@message") or failure.get("#text", "")
                    stack   = failure.get("#text")
                elif error:
                    err_msg = error.get("@message") or error.get("#text", "")

                results.append(TestResult(
                    name=test.get("@name", ""),
                    suite=suite_name,
                    file_path=test.get("@classname"),
                    status=status,
                    duration_ms=int(float(test.get("@time", 0)) * 1000),
                    error_message=err_msg,
                    stack_trace=stack,
                    browser=raw.get("_nexus_browser"),
                    platform=raw.get("_nexus_platform"),
                ))

        run = TestRun(
            project_id=project_id,
            tool="selenium",
            branch=raw.get("_nexus_branch"),
            environment=raw.get("_nexus_env"),
            started_at=datetime.utcnow(),
            results=results,
        )
        return run.compute_aggregates()


# ─── Appium (Mobile) ──────────────────────────────────────────────────────────
@register_adapter("appium")
class AppiumAdapter(BaseAdapter):
    """
    Parses Appium test results in JUnit-compatible JSON format.
    Extends SeleniumAdapter with mobile-specific fields.
    """

    def parse(self, raw: dict) -> TestRun:
        # Reuse the Selenium JUnit parsing, add mobile metadata
        from app.adapters.selenium_wdio import SeleniumAdapter
        base_run = SeleniumAdapter().parse(raw)

        for result in base_run.results:
            result.device   = raw.get("_nexus_device")
            result.platform = raw.get("_nexus_platform")   # "iOS", "Android"
            result.metadata["app_version"] = raw.get("_nexus_app_version")
            result.metadata["os_version"]  = raw.get("_nexus_os_version")

        base_run.tool = "appium"
        return base_run
