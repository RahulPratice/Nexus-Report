import pytest
from app.adapters.playwright import PlaywrightAdapter
from app.adapters.cypress import CypressAdapter
from app.adapters.all_adapters import JestAdapter, K6Adapter, PostmanAdapter
from app.models.utrs import TestStatus


# ─── Playwright ────────────────────────────────────────────────────────────
class TestPlaywrightAdapter:
    def _raw(self, **overrides):
        base = {
            "_nexus_project_id": "proj_test",
            "startTime": 1700000000000,
            "stats": {"duration": 12345},
            "suites": [
                {
                    "title": "auth",
                    "specs": [
                        {
                            "title": "login works",
                            "file": "tests/auth.spec.ts",
                            "tags": ["@smoke"],
                            "tests": [
                                {
                                    "status": "passed",
                                    "projectName": "chromium",
                                    "results": [{"status": "passed", "duration": 1200, "steps": [], "attachments": []}],
                                }
                            ],
                        },
                        {
                            "title": "logout fails",
                            "file": "tests/auth.spec.ts",
                            "tags": [],
                            "tests": [
                                {
                                    "status": "failed",
                                    "projectName": "chromium",
                                    "results": [
                                        {
                                            "status": "failed",
                                            "duration": 500,
                                            "error": {"message": "Expected true, got false", "stack": "at line 42"},
                                            "steps": [],
                                            "attachments": [
                                                {"name": "screenshot", "contentType": "image/png", "path": "/tmp/ss.png"}
                                            ],
                                        }
                                    ],
                                }
                            ],
                        },
                    ],
                }
            ],
        }
        base.update(overrides)
        return base

    def test_basic_parse(self):
        run = PlaywrightAdapter().parse(self._raw())
        assert run.total == 2
        assert run.passed == 1
        assert run.failed == 1
        assert run.pass_rate == 50.0
        assert run.tool == "playwright"

    def test_flaky_detection(self):
        raw = self._raw()
        raw["suites"][0]["specs"][0]["tests"][0]["results"] = [
            {"status": "failed", "duration": 800, "steps": [], "attachments": [], "error": {"message": "timeout"}},
            {"status": "passed", "duration": 1200, "steps": [], "attachments": []},
        ]
        run = PlaywrightAdapter().parse(raw)
        flaky = [r for r in run.results if r.status == TestStatus.FLAKY]
        assert len(flaky) == 1

    def test_screenshot_extracted(self):
        run = PlaywrightAdapter().parse(self._raw())
        failed = [r for r in run.results if r.status == TestStatus.FAILED][0]
        assert failed.screenshot_url == "/tmp/ss.png"

    def test_project_id_injected(self):
        run = PlaywrightAdapter().parse(self._raw())
        assert run.project_id == "proj_test"

    def test_tags_preserved(self):
        run = PlaywrightAdapter().parse(self._raw())
        smoke = [r for r in run.results if "@smoke" in r.tags]
        assert len(smoke) == 1


# ─── Jest ──────────────────────────────────────────────────────────────────
class TestJestAdapter:
    def _raw(self):
        return {
            "_nexus_project_id": "proj_jest",
            "startTime": 1700000000000,
            "testResults": [
                {
                    "testFilePath": "/app/tests/auth.test.ts",
                    "perfStats": {"start": 1700000000000, "end": 1700000005000},
                    "testResults": [
                        {
                            "title": "should login",
                            "ancestorTitles": ["AuthService"],
                            "status": "passed",
                            "duration": 230,
                            "failureMessages": [],
                        },
                        {
                            "title": "should reject bad password",
                            "ancestorTitles": ["AuthService"],
                            "status": "failed",
                            "duration": 150,
                            "failureMessages": ["Expected 401, got 200"],
                        },
                    ],
                }
            ],
        }

    def test_parse(self):
        run = JestAdapter().parse(self._raw())
        assert run.total == 2
        assert run.passed == 1
        assert run.failed == 1
        assert run.tool == "jest"

    def test_suite_name_includes_file(self):
        run = JestAdapter().parse(self._raw())
        assert "auth.test.ts" in run.results[0].suite


# ─── k6 ────────────────────────────────────────────────────────────────────
class TestK6Adapter:
    def _raw(self):
        return {
            "_nexus_project_id": "proj_k6",
            "metrics": {
                "http_req_duration": {
                    "thresholds": {"p(95)<500": True},
                    "values": {"avg": 120, "p(95)": 450, "p(99)": 498},
                },
                "http_req_failed": {
                    "thresholds": {"rate<0.01": False},
                    "values": {"rate": 0.025},
                },
            },
        }

    def test_parse(self):
        run = K6Adapter().parse(self._raw())
        assert run.total == 2
        assert run.passed == 1
        assert run.failed == 1
        assert run.tool == "k6"

    def test_p95_in_metadata(self):
        run = K6Adapter().parse(self._raw())
        duration_test = next(r for r in run.results if r.name == "http_req_duration")
        assert duration_test.metadata["p95"] == 450


# ─── UTRS ──────────────────────────────────────────────────────────────────
class TestUTRS:
    def test_compute_aggregates(self):
        from app.models.utrs import TestRun, TestResult, TestStatus
        from datetime import datetime

        run = TestRun(
            project_id="p1",
            tool="test",
            started_at=datetime.utcnow(),
            results=[
                TestResult(name="a", suite="s", status=TestStatus.PASSED, duration_ms=100),
                TestResult(name="b", suite="s", status=TestStatus.FAILED, duration_ms=200),
                TestResult(name="c", suite="s", status=TestStatus.SKIPPED, duration_ms=0),
                TestResult(name="d", suite="s", status=TestStatus.FLAKY,  duration_ms=300),
            ],
        )
        run.compute_aggregates()
        assert run.total   == 4
        assert run.passed  == 1
        assert run.failed  == 1
        assert run.skipped == 1
        assert run.flaky   == 1
        assert run.pass_rate == 25.0
