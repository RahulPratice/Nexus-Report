from fastapi import APIRouter, HTTPException, Header, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.db import Project, Run, TestResult as DBResult
from app.adapters.base import get_adapter
from app.workers.tasks import analyze_run_task, send_notifications_task
import redis.asyncio as aioredis
from app.core.config import settings
import json

router = APIRouter()


async def get_project_by_api_key(
    x_api_key: str = Header(...),
    db: AsyncSession = Depends(get_db),
) -> Project:
    result = await db.execute(
        select(Project).where(Project.api_key == x_api_key)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return project


@router.post("/ingest")
async def ingest_results(
    payload: dict,
    background_tasks: BackgroundTasks,
    project: Project = Depends(get_project_by_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Universal ingestion endpoint.
    Accepts raw output from any supported testing tool.
    The 'tool' field in the payload determines which adapter is used.
    """
    tool = payload.get("tool") or payload.get("_nexus_tool")
    if not tool:
        raise HTTPException(
            status_code=400,
            detail="Missing 'tool' field. e.g. 'playwright', 'cypress', 'jest'"
        )

    # Inject project context
    payload["_nexus_project_id"] = project.id

    try:
        adapter = get_adapter(tool)
        test_run = adapter.parse(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Parse error: {str(e)}")

    # Persist the Run
    db_run = Run(
        id=test_run.id,
        project_id=project.id,
        tool=test_run.tool,
        tool_version=test_run.tool_version,
        branch=test_run.branch,
        commit_sha=test_run.commit_sha,
        commit_message=test_run.commit_message,
        pr_number=test_run.pr_number,
        environment=test_run.environment,
        ci_provider=test_run.ci_provider,
        ci_run_url=test_run.ci_run_url,
        triggered_by=test_run.triggered_by,
        started_at=test_run.started_at,
        finished_at=test_run.finished_at,
        duration_ms=test_run.duration_ms,
        total=test_run.total,
        passed=test_run.passed,
        failed=test_run.failed,
        skipped=test_run.skipped,
        flaky=test_run.flaky,
        pass_rate=test_run.pass_rate,
        run_metadata=test_run.metadata,
    )
    db.add(db_run)

    # Persist individual test results
    db_results = []
    for r in test_run.results:
        db_result = DBResult(
            id=r.id,
            run_id=test_run.id,
            project_id=project.id,
            name=r.name,
            suite=r.suite,
            file_path=r.file_path,
            status=r.status.value,
            duration_ms=r.duration_ms,
            started_at=r.started_at,
            error_message=r.error_message,
            stack_trace=r.stack_trace,
            retry_count=r.retry_count,
            browser=r.browser,
            platform=r.platform,
            device=r.device,
            screenshot_url=r.screenshot_url,
            video_url=r.video_url,
            trace_url=r.trace_url,
            tags=r.tags,
            steps=[s.model_dump() for s in r.steps],
            result_metadata=r.metadata,
        )
        db_results.append(db_result)
        db.add(db_result)

    await db.flush()

    # Broadcast to live WebSocket subscribers
    redis = aioredis.from_url(settings.redis_url)
    await redis.publish(
        f"run:{test_run.id}",
        json.dumps({
            "event": "run_complete",
            "run_id": test_run.id,
            "total": test_run.total,
            "passed": test_run.passed,
            "failed": test_run.failed,
            "pass_rate": test_run.pass_rate,
        }),
    )
    await redis.aclose()

    # Queue background AI analysis + notifications
    background_tasks.add_task(analyze_run_task.delay, test_run.id)
    background_tasks.add_task(send_notifications_task.delay, test_run.id, project.name)

    return {
        "run_id": test_run.id,
        "total": test_run.total,
        "passed": test_run.passed,
        "failed": test_run.failed,
        "pass_rate": test_run.pass_rate,
        "message": "Run ingested. AI analysis queued.",
    }
