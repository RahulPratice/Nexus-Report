# Contributing to NexusReport

Thank you for your interest in contributing! This document covers everything you need to get started.

---

## Ways to contribute

- **Bug reports** — open an issue with steps to reproduce
- **New adapters** — add support for a testing tool we don't cover yet
- **Feature requests** — open a discussion before building large features
- **Documentation** — fix typos, improve examples, write guides
- **Code** — bug fixes, performance improvements, new features

---

## Local development setup

### Prerequisites
- Docker + Docker Compose
- Python 3.11+
- Node.js 20+
- Git

### 1. Fork and clone

```bash
git clone https://github.com/YOUR_USERNAME/nexusreport.git
cd nexusreport
cp .env.example .env
```

### 2. Start the stack

```bash
docker compose up -d db redis minio
```

### 3. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend runs at http://localhost:8000. API docs at http://localhost:8000/docs.

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at http://localhost:3000.

---

## Writing a new adapter

Adding support for a new testing tool is the most valuable contribution.

### Step 1 — Create the adapter file

```python
# backend/app/adapters/my_tool.py
from app.adapters.base import BaseAdapter, register_adapter
from app.models.utrs import TestRun, TestResult, TestStatus
from datetime import datetime


@register_adapter("my_tool")
class MyToolAdapter(BaseAdapter):
    """
    Parses My Tool's JSON output.
    Compatible with: my-tool >= 2.0.0
    """

    def parse(self, raw: dict) -> TestRun:
        results = []

        for test in raw.get("tests", []):
            results.append(TestResult(
                name=test["name"],
                suite=test.get("suite", "default"),
                status=self._map_status(test["result"]),
                duration_ms=test.get("duration", 0),
                error_message=test.get("error"),
            ))

        run = TestRun(
            project_id=raw.get("_nexus_project_id", ""),
            tool="my_tool",
            started_at=datetime.utcnow(),
            results=results,
        )
        return run.compute_aggregates()

    def _map_status(self, raw_status: str) -> TestStatus:
        return {
            "pass": TestStatus.PASSED,
            "fail": TestStatus.FAILED,
            "skip": TestStatus.SKIPPED,
        }.get(raw_status, TestStatus.FAILED)
```

### Step 2 — Register it in main.py

```python
# backend/app/main.py
import app.adapters.my_tool   # noqa — registers the adapter
```

### Step 3 — Write tests

```python
# backend/tests/adapters/test_my_tool.py
from app.adapters.my_tool import MyToolAdapter

def test_basic_parse():
    raw = {
        "_nexus_project_id": "proj_123",
        "tests": [
            {"name": "login works", "suite": "auth", "result": "pass", "duration": 1200},
            {"name": "signup fails", "suite": "auth", "result": "fail", "error": "AssertionError"},
        ],
    }
    adapter = MyToolAdapter()
    run = adapter.parse(raw)

    assert run.total == 2
    assert run.passed == 1
    assert run.failed == 1
    assert run.pass_rate == 50.0
```

### Step 4 — Add a fixture

Add a sample JSON file at `backend/tests/fixtures/my_tool_sample.json` so others can test with it.

---

## Pull request checklist

- [ ] Code follows the existing style (Black for Python, ESLint for TypeScript)
- [ ] Tests added or updated
- [ ] All existing tests pass (`pytest` / `npm run lint`)
- [ ] If adding an adapter: sample fixture file included
- [ ] PR description explains what changed and why

---

## Code style

**Python:** Black + isort. Run before committing:
```bash
black app/ tests/
isort app/ tests/
```

**TypeScript:** ESLint + Prettier:
```bash
npm run lint
```

---

## Commit message format

```
type(scope): short description

Examples:
feat(adapter): add JUnit XML adapter
fix(flaky): correct score calculation for low sample sizes
docs(readme): add Vitest integration example
chore(ci): update Node to v20
```

Types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `perf`

---

## Getting help

- Open a [GitHub Discussion](https://github.com/your-org/nexusreport/discussions) for questions
- Join our [Discord](https://discord.gg/nexusreport)
- Tag issues with `good first issue` for beginner-friendly tasks
