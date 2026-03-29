import json
import asyncio
from openai import AsyncOpenAI
from app.core.config import settings
from app.models.utrs import TestResult, AIAnalysis, ErrorCategory

client = AsyncOpenAI(api_key=settings.openai_api_key)

ERROR_CATEGORIES = [c.value for c in ErrorCategory]

SYSTEM_PROMPT = """You are a senior QA engineer and test automation expert.
Analyze test failures and respond with structured JSON only — no preamble, no markdown."""

ANALYSIS_PROMPT = """Analyze this test failure and return ONLY a JSON object.

Test name: {name}
Suite: {suite}
Tool: {tool}
Error message: {error}
Stack trace: {stack}

Return exactly this JSON shape:
{{
  "category": "<one of: {categories}>",
  "confidence": <float 0.0-1.0>,
  "root_cause": "<one concise sentence>",
  "suggested_fix": "<2-3 actionable steps separated by \\n>",
  "is_likely_flaky": <true|false>
}}"""


async def analyze_failure(result: TestResult, tool: str) -> AIAnalysis:
    """Call GPT-4o to classify and explain a test failure."""
    if not settings.openai_api_key:
        return AIAnalysis()

    prompt = ANALYSIS_PROMPT.format(
        name=result.name,
        suite=result.suite,
        tool=tool,
        error=result.error_message or "No error message",
        stack=(result.stack_trace or "")[:3000],
        categories=", ".join(ERROR_CATEGORIES),
    )

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=500,
        )
        data = json.loads(response.choices[0].message.content)
        return AIAnalysis(
            category=data.get("category", ErrorCategory.UNKNOWN),
            confidence=float(data.get("confidence", 0.0)),
            root_cause=data.get("root_cause", ""),
            suggested_fix=data.get("suggested_fix", ""),
            is_likely_flaky=bool(data.get("is_likely_flaky", False)),
        )
    except Exception as e:
        return AIAnalysis(root_cause=f"Analysis failed: {str(e)}")


async def analyze_run_failures(results: list[TestResult], tool: str) -> list[TestResult]:
    """Analyze all failed tests in a run concurrently (max 10 at once)."""
    failed = [r for r in results if r.error_message]
    semaphore = asyncio.Semaphore(10)

    async def analyze_with_limit(result: TestResult):
        async with semaphore:
            result.ai_analysis = await analyze_failure(result, tool)
        return result

    await asyncio.gather(*[analyze_with_limit(r) for r in failed])
    return results
