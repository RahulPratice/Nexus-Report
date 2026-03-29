from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.core.database import get_db
from app.models.db import Run, TestResult

router = APIRouter()


@router.get("/runs")
async def list_runs(
    project_id: str = Query(...),
    branch: str | None = Query(None),
    tool: str | None = Query(None),
    environment: str | None = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Run).where(Run.project_id == project_id)
    if branch:
        stmt = stmt.where(Run.branch == branch)
    if tool:
        stmt = stmt.where(Run.tool == tool)
    if environment:
        stmt = stmt.where(Run.environment == environment)

    stmt = stmt.order_by(desc(Run.started_at)).limit(limit).offset(offset)
    result = await db.execute(stmt)
    runs = result.scalars().all()

    return [
        {
            "id": r.id,
            "tool": r.tool,
            "branch": r.branch,
            "environment": r.environment,
            "started_at": r.started_at,
            "duration_ms": r.duration_ms,
            "total": r.total,
            "passed": r.passed,
            "failed": r.failed,
            "pass_rate": r.pass_rate,
            "commit_sha": r.commit_sha[:7] if r.commit_sha else None,
        }
        for r in runs
    ]


@router.get("/runs/{run_id}")
async def get_run(run_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/runs/{run_id}/results")
async def get_run_results(
    run_id: str,
    status: str | None = Query(None),
    search: str | None = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(TestResult).where(TestResult.run_id == run_id)
    if status:
        stmt = stmt.where(TestResult.status == status)
    if search:
        stmt = stmt.where(TestResult.name.ilike(f"%{search}%"))

    stmt = stmt.order_by(TestResult.status, TestResult.name).limit(limit).offset(offset)
    result = await db.execute(stmt)
    tests = result.scalars().all()

    return [
        {
            "id": t.id,
            "name": t.name,
            "suite": t.suite,
            "status": t.status,
            "duration_ms": t.duration_ms,
            "error_message": t.error_message,
            "ai_category": t.ai_category,
            "ai_root_cause": t.ai_root_cause,
            "ai_fix": t.ai_fix,
            "ai_confidence": t.ai_confidence,
            "flaky_score": t.flaky_score,
            "retry_count": t.retry_count,
            "browser": t.browser,
            "screenshot_url": t.screenshot_url,
            "video_url": t.video_url,
            "trace_url": t.trace_url,
            "tags": t.tags,
        }
        for t in tests
    ]


@router.get("/runs/{run_id}/results/{result_id}")
async def get_test_result(
    run_id: str,
    result_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TestResult).where(
            TestResult.id == result_id,
            TestResult.run_id == run_id,
        )
    )
    test = result.scalar_one_or_none()
    if not test:
        raise HTTPException(status_code=404, detail="Test result not found")
    return {
        **test.__dict__,
        "steps": test.steps,
        "comments": [
            {"author": c.author, "body": c.body, "created_at": c.created_at}
            for c in test.comments
        ],
    }
