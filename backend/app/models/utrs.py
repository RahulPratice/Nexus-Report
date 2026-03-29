"""
Unified Test Result Schema (UTRS)
Every adapter normalizes its tool-specific output to this schema.
This is the contract that makes NexusReport tool-agnostic.
"""
from pydantic import BaseModel, Field
from typing import Optional, Any
from enum import Enum
from datetime import datetime
import uuid


class TestStatus(str, Enum):
    PASSED  = "passed"
    FAILED  = "failed"
    SKIPPED = "skipped"
    FLAKY   = "flaky"
    PENDING = "pending"
    BROKEN  = "broken"


class ErrorCategory(str, Enum):
    ASSERTION         = "assertion_failure"
    TIMEOUT           = "timeout"
    NETWORK           = "network_error"
    ELEMENT_NOT_FOUND = "element_not_found"
    AUTH              = "auth_failure"
    DATA              = "data_issue"
    ENVIRONMENT       = "environment_issue"
    FLAKY_RACE        = "flaky_race_condition"
    UNKNOWN           = "unknown"


class TestStep(BaseModel):
    name: str
    status: TestStatus
    duration_ms: int = 0
    error: Optional[str] = None
    screenshot_url: Optional[str] = None
    attachment_urls: list[str] = Field(default_factory=list)


class AIAnalysis(BaseModel):
    category: ErrorCategory = ErrorCategory.UNKNOWN
    confidence: float = 0.0
    root_cause: str = ""
    suggested_fix: str = ""
    is_likely_flaky: bool = False


class TestResult(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    suite: str
    file_path: Optional[str] = None
    status: TestStatus
    duration_ms: int = 0
    started_at: Optional[datetime] = None

    # Failure info
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    diff: Optional[str] = None

    # AI-enriched fields (populated async after ingestion)
    ai_analysis: Optional[AIAnalysis] = None
    flaky_score: Optional[float] = None       # 0.0 (stable) → 1.0 (very flaky)

    # Steps / attachments
    steps: list[TestStep] = Field(default_factory=list)
    screenshot_url: Optional[str] = None
    video_url: Optional[str] = None
    trace_url: Optional[str] = None

    # Context
    tags: list[str] = Field(default_factory=list)
    retry_count: int = 0
    worker_index: Optional[int] = None
    browser: Optional[str] = None
    platform: Optional[str] = None
    device: Optional[str] = None              # for Appium

    # Tool-specific extras
    metadata: dict[str, Any] = Field(default_factory=dict)


class TestRun(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str
    tool: str                                  # "playwright", "cypress", "jest", etc.
    tool_version: Optional[str] = None

    # Git context
    branch: Optional[str] = None
    commit_sha: Optional[str] = None
    commit_message: Optional[str] = None
    pr_number: Optional[str] = None
    repository_url: Optional[str] = None

    # Environment
    environment: Optional[str] = None          # "staging", "production", "local"
    ci_provider: Optional[str] = None          # "github_actions", "gitlab_ci", etc.
    ci_run_url: Optional[str] = None
    triggered_by: Optional[str] = None

    # Timing
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None
    duration_ms: int = 0

    # Aggregates
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    flaky: int = 0
    pass_rate: float = 0.0

    # Results
    results: list[TestResult] = Field(default_factory=list)

    # Run-level metadata
    metadata: dict[str, Any] = Field(default_factory=dict)

    def compute_aggregates(self):
        self.total   = len(self.results)
        self.passed  = sum(1 for r in self.results if r.status == TestStatus.PASSED)
        self.failed  = sum(1 for r in self.results if r.status == TestStatus.FAILED)
        self.skipped = sum(1 for r in self.results if r.status == TestStatus.SKIPPED)
        self.flaky   = sum(1 for r in self.results if r.status == TestStatus.FLAKY)
        self.pass_rate = (self.passed / self.total * 100) if self.total > 0 else 0.0
        return self
