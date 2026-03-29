"""
Flaky Test Detection Engine
Computes a flakiness score (0.0 = stable, 1.0 = very flaky) for each test
based on its historical run data over a configurable time window.
"""
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.db import TestResult


async def compute_flaky_score(
    db: AsyncSession,
    test_name: str,
    project_id: str,
    suite: str,
    days: int = 14,
) -> float:
    """
    Flakiness score formula:
      score = (inconsistency_rate × 0.5)
            + (retry_rate         × 0.3)
            + (recent_fail_rate   × 0.2)

    inconsistency_rate: how often the test flips between pass/fail
    retry_rate:         average retries needed before resolution
    recent_fail_rate:   fail rate in the last 5 runs (more weight on recent)
    """
    stmt = (
        select(TestResult.status, TestResult.retry_count)
        .where(
            TestResult.project_id == project_id,
            TestResult.name == test_name,
            TestResult.suite == suite,
        )
        .order_by(TestResult.started_at.desc())
        .limit(50)
    )
    rows = (await db.execute(stmt)).all()

    if len(rows) < 3:
        return 0.0

    statuses = [r.status for r in rows]
    retries  = [r.retry_count for r in rows]

    # Inconsistency: fraction of consecutive runs that changed status
    transitions = sum(
        1 for i in range(1, len(statuses)) if statuses[i] != statuses[i - 1]
    )
    inconsistency_rate = transitions / max(len(statuses) - 1, 1)

    # Retry rate: normalized to 0-1 assuming >3 retries = fully flaky
    avg_retries = sum(retries) / len(retries)
    retry_score = min(avg_retries / 3.0, 1.0)

    # Recent fail rate (last 5 runs)
    recent = statuses[:5]
    recent_fail_rate = sum(1 for s in recent if s in ("failed", "broken")) / len(recent)

    score = (
        inconsistency_rate * 0.50
        + retry_score      * 0.30
        + recent_fail_rate * 0.20
    )
    return round(min(score, 1.0), 4)


async def label_flaky_score(score: float) -> str:
    """Human-readable label for the flaky score."""
    if score >= 0.7:
        return "very flaky"
    if score >= 0.4:
        return "flaky"
    if score >= 0.2:
        return "unstable"
    return "stable"


async def get_flakiest_tests(
    db: AsyncSession,
    project_id: str,
    limit: int = 20,
):
    """Return the most flaky tests in a project."""
    stmt = (
        select(
            TestResult.name,
            TestResult.suite,
            func.avg(TestResult.flaky_score).label("avg_score"),
            func.count(TestResult.id).label("run_count"),
        )
        .where(
            TestResult.project_id == project_id,
            TestResult.flaky_score.isnot(None),
        )
        .group_by(TestResult.name, TestResult.suite)
        .order_by(func.avg(TestResult.flaky_score).desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.all()
