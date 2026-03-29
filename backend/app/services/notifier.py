import httpx
from app.core.config import settings
from app.models.utrs import TestRun


async def notify_run_complete(run: TestRun, project_name: str):
    """Send notifications when a run completes, if configured."""
    if settings.slack_webhook_url:
        await _notify_slack(run, project_name)
    if settings.teams_webhook_url:
        await _notify_teams(run, project_name)


async def _notify_slack(run: TestRun, project_name: str):
    status_emoji = "✅" if run.failed == 0 else "❌"
    color        = "#36a64f" if run.failed == 0 else "#ff0000"

    payload = {
        "attachments": [{
            "color": color,
            "title": f"{status_emoji} {project_name} — {run.tool} run completed",
            "fields": [
                {"title": "Passed",   "value": str(run.passed),       "short": True},
                {"title": "Failed",   "value": str(run.failed),       "short": True},
                {"title": "Pass rate","value": f"{run.pass_rate:.1f}%","short": True},
                {"title": "Branch",   "value": run.branch or "—",     "short": True},
            ],
            "footer": "NexusReport",
        }]
    }

    async with httpx.AsyncClient() as client:
        await client.post(settings.slack_webhook_url, json=payload)


async def _notify_teams(run: TestRun, project_name: str):
    status = "✅ Passed" if run.failed == 0 else f"❌ {run.failed} Failed"
    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": "0076D7" if run.failed == 0 else "FF0000",
        "summary": f"{project_name} test run completed",
        "sections": [{
            "activityTitle": f"{project_name} — {run.tool}",
            "activitySubtitle": status,
            "facts": [
                {"name": "Passed",    "value": str(run.passed)},
                {"name": "Failed",    "value": str(run.failed)},
                {"name": "Pass Rate", "value": f"{run.pass_rate:.1f}%"},
                {"name": "Branch",    "value": run.branch or "—"},
            ],
        }],
    }

    async with httpx.AsyncClient() as client:
        await client.post(settings.teams_webhook_url, json=payload)
