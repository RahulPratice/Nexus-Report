from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.core.database import get_db
from app.models.db import Run, TestResult
from app.services.flaky_detector import get_flakiest_tests
from datetime import datetime, timedelta

router = APIRouter()


@router.get("/analytics/pass-rate-trend")
async def pass_rate_trend(
    project_id: str = Query(...),
    days: int = Query(30, le=90),
    branch: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Pass rate over time — one data point per run."""
    since = datetime.utcnow() - timedelta(days=days)
    stmt = (
        select(Run.started_at, Run.pass_rate, Run.tool, Run.branch, Run.failed, Run.total)
        .where(Run.project_id == project_id, Run.started_at >= since)
    )
    if branch:
        stmt = stmt.where(Run.branch == branch)
    stmt = stmt.order_by(Run.started_at)

    result = await db.execute(stmt)
    rows = result.all()
    return [
        {
            "date": r.started_at.isoformat(),
            "pass_rate": round(r.pass_rate, 2),
            "tool": r.tool,
            "branch": r.branch,
            "failed": r.failed,
            "total": r.total,
        }
        for r in rows
    ]


@router.get("/analytics/flaky-tests")
async def flaky_tests(
    project_id: str = Query(...),
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Top flakiest tests in a project."""
    rows = await get_flakiest_tests(db, project_id, limit)
    return [
        {
            "name": r.name,
            "suite": r.suite,
            "flaky_score": round(float(r.avg_score), 4),
            "run_count": r.run_count,
            "label": _flaky_label(float(r.avg_score)),
        }
        for r in rows
    ]


@router.get("/analytics/error-breakdown")
async def error_breakdown(
    project_id: str = Query(...),
    days: int = Query(14),
    db: AsyncSession = Depends(get_db),
):
    """Count of AI-classified error categories for the last N days."""
    since = datetime.utcnow() - timedelta(days=days)
    stmt = (
        select(TestResult.ai_category, func.count(TestResult.id).label("count"))
        .join(Run, Run.id == TestResult.run_id)
        .where(
            Run.project_id == project_id,
            Run.started_at >= since,
            TestResult.ai_category.isnot(None),
        )
        .group_by(TestResult.ai_category)
        .order_by(desc("count"))
    )
    result = await db.execute(stmt)
    return [{"category": r.ai_category, "count": r.count} for r in result.all()]


@router.get("/analytics/multi-project")
async def multi_project_summary(
    project_ids: list[str] = Query(...),
    days: int = Query(7),
    db: AsyncSession = Depends(get_db),
):
    """Cross-project health comparison — for the hub dashboard."""
    since = datetime.utcnow() - timedelta(days=days)
    results = []

    for pid in project_ids:
        stmt = (
            select(
                func.avg(Run.pass_rate).label("avg_pass_rate"),
                func.count(Run.id).label("run_count"),
                func.sum(Run.failed).label("total_failures"),
            )
            .where(Run.project_id == pid, Run.started_at >= since)
        )
        row = (await db.execute(stmt)).one()
        results.append({
            "project_id": pid,
            "avg_pass_rate": round(float(row.avg_pass_rate or 0), 2),
            "run_count": row.run_count,
            "total_failures": row.total_failures or 0,
        })

    return results


@router.get("/analytics/duration-trend")
async def duration_trend(
    project_id: str = Query(...),
    days: int = Query(30),
    db: AsyncSession = Depends(get_db),
):
    """Average test duration trend — helps spot slow-test regressions."""
    since = datetime.utcnow() - timedelta(days=days)
    stmt = (
        select(
            func.date_trunc("day", Run.started_at).label("day"),
            func.avg(Run.duration_ms).label("avg_duration_ms"),
            func.count(Run.id).label("run_count"),
        )
        .where(Run.project_id == project_id, Run.started_at >= since)
        .group_by("day")
        .order_by("day")
    )
    result = await db.execute(stmt)
    return [
        {
            "day": r.day.date().isoformat(),
            "avg_duration_ms": int(r.avg_duration_ms or 0),
            "run_count": r.run_count,
        }
        for r in result.all()
    ]


def _flaky_label(score: float) -> str:
    if score >= 0.7: return "very flaky"
    if score >= 0.4: return "flaky"
    if score >= 0.2: return "unstable"
    return "stable"
