import asyncio
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "nexusreport",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


@celery_app.task(name="analyze_run", bind=True, max_retries=3)
def analyze_run_task(self, run_id: str):
    """
    Background task: run AI analysis on all failed tests in a run.
    Triggered after ingestion completes.
    """
    asyncio.run(_analyze_run(run_id))


async def _analyze_run(run_id: str):
    from app.core.database import AsyncSessionLocal
    from app.models.db import Run, TestResult as DBResult
    from app.services.ai_analyzer import analyze_failure
    from app.services.flaky_detector import compute_flaky_score
    from app.models.utrs import TestResult as UTRSResult
    from sqlalchemy import select, update

    async with AsyncSessionLocal() as db:
        # Fetch failed tests for this run
        result = await db.execute(
            select(DBResult).where(
                DBResult.run_id == run_id,
                DBResult.status.in_(["failed", "broken"]),
            )
        )
        failed_tests = result.scalars().all()

        # Fetch run for tool info
        run_result = await db.execute(select(Run).where(Run.id == run_id))
        run = run_result.scalar_one_or_none()
        if not run:
            return

        for test in failed_tests:
            # AI analysis
            utrs_test = UTRSResult(
                id=test.id,
                name=test.name,
                suite=test.suite,
                status=test.status,
                error_message=test.error_message,
                stack_trace=test.stack_trace,
            )
            analysis = await analyze_failure(utrs_test, run.tool)

            # Flaky score
            flaky = await compute_flaky_score(
                db, test.name, test.project_id, test.suite
            )

            await db.execute(
                update(DBResult)
                .where(DBResult.id == test.id)
                .values(
                    ai_category=analysis.category,
                    ai_root_cause=analysis.root_cause,
                    ai_fix=analysis.suggested_fix,
                    ai_confidence=analysis.confidence,
                    flaky_score=flaky,
                )
            )

        await db.commit()


@celery_app.task(name="send_notifications")
def send_notifications_task(run_id: str, project_name: str):
    """Send Slack/Teams notifications after a run is processed."""
    asyncio.run(_send_notifications(run_id, project_name))


async def _send_notifications(run_id: str, project_name: str):
    from app.core.database import AsyncSessionLocal
    from app.models.db import Run
    from app.services.notifier import notify_run_complete
    from app.models.utrs import TestRun
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Run).where(Run.id == run_id))
        run_db = result.scalar_one_or_none()
        if not run_db:
            return

        run = TestRun(
            id=run_db.id,
            project_id=run_db.project_id,
            tool=run_db.tool,
            branch=run_db.branch,
            passed=run_db.passed,
            failed=run_db.failed,
            pass_rate=run_db.pass_rate,
        )
        await notify_run_complete(run, project_name)
