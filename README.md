# NexusReport 🧪

> **The open-source, AI-powered test reporting platform that works with every testing tool.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![React 18](https://img.shields.io/badge/react-18-61DAFB.svg)](https://reactjs.org)
[![Docker](https://img.shields.io/badge/docker-ready-2496ED.svg)](docker-compose.yml)

---

## What is NexusReport?

NexusReport is an **advanced, self-hostable test reporting platform** that ingests results from any testing tool, provides AI-powered failure analysis, detects flaky tests, and gives your entire team a unified real-time view of quality across all projects.

### Why NexusReport over Allure?

| Feature | Allure | NexusReport |
|---|---|---|
| Universal adapter layer | Partial | ✅ All major tools |
| AI failure classification | ❌ | ✅ GPT-4o powered |
| Flaky test scoring | Basic | ✅ ML-based trend scoring |
| Real-time live dashboard | ❌ | ✅ WebSocket streaming |
| Multi-project comparison | ❌ | ✅ Cross-repo health hub |
| Team collaboration | ❌ | ✅ Comments + assignments |
| Custom KPIs | ❌ | ✅ Fully configurable |
| Self-hostable | ✅ | ✅ Docker one-liner |

---

## Supported Testing Tools

| Tool | Adapter | Status |
|---|---|---|
| Playwright | `@nexusreport/playwright-reporter` | ✅ Stable |
| Cypress | `@nexusreport/cypress-plugin` | ✅ Stable |
| Jest / Vitest | `@nexusreport/jest-reporter` | ✅ Stable |
| Selenium / WebdriverIO | Python adapter | ✅ Stable |
| Postman / Newman | CLI reporter | ✅ Stable |
| k6 (performance) | Threshold adapter | ✅ Stable |
| Appium (mobile) | Session adapter | ✅ Stable |

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/your-org/nexusreport.git
cd nexusreport

# 2. Copy env file and set your OpenAI key
cp .env.example .env

# 3. Start everything
docker compose up -d

# 4. Open the dashboard
open http://localhost:3000
```

---

## Playwright Integration (30 seconds)

```bash
npm install @nexusreport/playwright-reporter
```

```typescript
// playwright.config.ts
import { defineConfig } from '@playwright/test';

export default defineConfig({
  reporter: [
    ['@nexusreport/playwright-reporter', {
      serverUrl: 'http://localhost:8000',
      apiKey: 'your-api-key',
      projectId: 'your-project-id',
    }]
  ],
});
```

---

## Architecture

```
Testing Tools → Adapter Layer → FastAPI Backend → PostgreSQL + TimescaleDB
                                      ↓                      ↓
                               AI Analyzer              Redis Cache
                                      ↓
                              React Dashboard (Real-time WebSocket)
```

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full system design.

---

## Development Setup

### Prerequisites
- Docker + Docker Compose
- Python 3.11+
- Node.js 20+

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

MIT — free for personal and commercial use.
