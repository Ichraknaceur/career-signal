# CareerSignal

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B?logo=streamlit&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?logo=sqlite&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-Browser_Automation-2EAD33?logo=playwright&logoColor=white)
![Anthropic](https://img.shields.io/badge/Anthropic-LLM-191919)
![OpenAI](https://img.shields.io/badge/OpenAI-LLM-412991?logo=openai&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Containers-2496ED?logo=docker&logoColor=white)
![Pytest](https://img.shields.io/badge/Pytest-Tests-0A9EDC?logo=pytest&logoColor=white)
![Ruff](https://img.shields.io/badge/Ruff-Lint-FCC21B?logo=ruff&logoColor=111111)
![MyPy](https://img.shields.io/badge/MyPy-Types-2A6DB2?logo=python&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-CI/CD-2088FF?logo=githubactions&logoColor=white)

CareerSignal is a job-search operating system designed to help technical
candidates build visibility, grow their network, and convert that momentum
into real career opportunities.

It combines:

- content generation for Medium and LinkedIn
- editorial scheduling and autopublishing
- LinkedIn outreach to peers and tech recruiters
- technical watch on topics and keywords
- a future-ready foundation for job-posting tracking

This repository currently contains:

- the existing multi-agent product implementation
- a new target architecture for the refactor
- a minimal SQLite schema
- Docker, Makefile, and CI/CD foundations
- a small FastAPI layer for feature testing

## Product Positioning

CareerSignal is built around a simple idea:

1. Create professional signal with relevant public content.
2. Turn that signal into stronger networking conversations.
3. Track opportunities, recruiters, and outreach activity.
4. Feed the whole system with technical and market watch.

In practice, the platform is meant to help an AI/Data candidate:

- publish consistently
- build a stronger LinkedIn presence
- reach out to relevant people with better context
- monitor job opportunities and trends
- centralize visibility, outreach, and follow-up workflows

## Core Features

### 1. Content Engine

- Generate Medium articles from a topic, URL, PDF, GitHub repo, or raw idea
- Generate LinkedIn posts from the same source material
- Use a QA loop before publication
- Support multiple LLM providers

### 2. Publishing Engine

- Build a LinkedIn content calendar
- Approve, edit, reject, and publish posts
- Autopublish approved posts when they become due
- Keep publication state and history

### 3. Networking Engine

- Search LinkedIn profiles and recruiter-related targets
- Enrich profile data with scraping
- Generate personalized connection notes
- Track outreach statuses and rate limits

### 4. Watch Engine

- Collect articles from RSS and scraping sources
- Summarize technical content
- Suggest LinkedIn posts from watch articles
- Prepare a future keyword-driven watch workflow

### 5. API and Refactor Foundation

- Expose testing endpoints with FastAPI
- Initialize and validate the SQLite schema
- Prepare the migration away from fragmented JSON storage

## Current Architecture

The repository is in transition between a working prototype and a cleaner,
market-facing platform architecture.

### Existing Runtime Areas

- `agents/`
  Specialized LLM agents for ingestion, strategy, writing, QA, outreach, and watch
- `pipelines/`
  Orchestration flows for Medium, scheduling, outreach, watch, and autopublish
- `tools/`
  Platform integrations, storage helpers, scraper utilities, and file/web tools
- `ui/`
  Streamlit interface

### Target Refactor Areas

- `app/`
  Runtime adapters such as UI, API, CLI, and background workers
- `domain/`
  Business rules and use cases
- `services/`
  External integrations such as LinkedIn, Medium, RSS, and LLM providers
- `storage/`
  SQLite, migrations, and repositories
- `observability/`
  Structured logging, workflow runs, and execution events

More details:

- [Documentation index](docs/README.md)
- [Target architecture](docs/architecture.md)
- [Target repo structure](docs/repo-structure.md)
- [Minimal SQLite schema](docs/database.md)
- [Docker, Makefile, and CI/CD](docs/devops.md)

## Repository Structure

```text
career-signal/
├── agents/
├── app/
│   ├── api/
│   ├── ui/
│   └── workers/
├── core/
├── data/
├── docker/
│   └── entrypoints/
├── docs/
├── domain/
├── observability/
├── orchestrator/
├── pipelines/
├── services/
├── storage/
├── tests/
├── tools/
└── ui/
```

## Tech Stack

### Application

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-Frontend-FF4B4B?logo=streamlit&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Storage-003B57?logo=sqlite&logoColor=white)

### AI and Automation

![Anthropic](https://img.shields.io/badge/Anthropic-Claude-191919)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT-412991?logo=openai&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-Automation-2EAD33?logo=playwright&logoColor=white)

### DevOps and Quality

![Docker](https://img.shields.io/badge/Docker-Containers-2496ED?logo=docker&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-CI/CD-2088FF?logo=githubactions&logoColor=white)
![Pytest](https://img.shields.io/badge/Pytest-Testing-0A9EDC?logo=pytest&logoColor=white)
![Ruff](https://img.shields.io/badge/Ruff-Linting-FCC21B?logo=ruff&logoColor=111111)
![MyPy](https://img.shields.io/badge/MyPy-Type_Checking-2A6DB2?logo=python&logoColor=white)

## Quick Start

### 1. Clone and enter the project

```bash
git clone <your-repo-url>
cd career-signal
```

If your local folder is still named differently, use your current folder name.

### 2. Create environment variables

```bash
cp .env.example .env
```

Then fill in the values you need, especially:

- `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`
- `LINKEDIN_EMAIL`
- `LINKEDIN_PASSWORD`
- `DATABASE_PATH`

### 3. Install dependencies

```bash
make dev-install
```

### 4. Initialize the database

```bash
make db-init
```

This creates the SQLite database, by default at:

- `data/app.db`

## Run Locally

### Streamlit UI

```bash
make ui
```

Then open:

- [http://localhost:8501](http://localhost:8501)

### FastAPI

```bash
make api
```

Then open:

- [http://localhost:8000/docs](http://localhost:8000/docs)
- [http://localhost:8000/health](http://localhost:8000/health)

### LinkedIn Autopublish Worker

```bash
make autopublish
```

## Run With Docker

### UI + API

```bash
docker compose up --build
```

Available services:

- UI: [http://localhost:8501](http://localhost:8501)
- API: [http://localhost:8000/docs](http://localhost:8000/docs)

### UI + API + Autopublish Worker

```bash
docker compose --profile automation up --build
```

## FastAPI Endpoints Available

Current API endpoints:

- `GET /health`
- `POST /db/init`
- `GET /scheduled-posts`
- `POST /publishing/linkedin/autopublish/run-once`

These endpoints are intended as a first test layer so features can be exercised
without going through Streamlit.

## Useful Commands

```bash
make help
make ui
make api
make autopublish
make db-init
make docs
make tree
make test
make lint
make typecheck
make compile
make ci
```

## Testing

### Targeted checks

```bash
python3 -m pytest tests/storage/test_init_db.py tests/test_scheduler_tools.py tests/test_linkedin_autopublish.py tests/api/test_api.py -q
python3 -m compileall agents app core domain observability orchestrator pipelines services storage tools ui
```

### Full local validation

```bash
make ci
```

## Data and Persistence

The project currently uses a mix of legacy JSON storage and new SQLite
foundations.

### Existing legacy files

- `data/schedule.json`
- `data/outreach.json`
- `data/veille_sources.json`
- `data/veille_articles.json`

### New foundation

- `data/app.db`

The goal is to progressively migrate business-critical workflows from JSON to
SQLite so execution history, workflow states, and operational traces become
more reliable.

## CI/CD

GitHub Actions workflows are included for:

- code quality
- tests
- Python compilation checks
- Docker build validation
- container publishing to GHCR

See:

- [CI workflow](.github/workflows/ci.yml)
- [CD workflow](.github/workflows/cd.yml)

## Why This Project Matters

This project is not just a content generator.

It is meant to demonstrate how AI workflows can support a real market-facing
problem:

- professional visibility
- networking quality
- job opportunity tracking
- operational discipline across multiple channels

For a portfolio, it showcases:

- multi-agent workflow design
- LLM orchestration
- scraping and automation
- product thinking
- workflow observability
- API design
- Docker and CI/CD setup

## Roadmap

### Near term

- Migrate scheduling from JSON to SQLite
- Add repository implementations
- Add workflow run persistence
- Expand FastAPI coverage for key use cases

### Next phase

- Add job tracking workflows and endpoints
- Add recruiter and company entities
- Add stronger observability and audit trails
- Add a cleaner API-first service layer behind the UI

### Longer term

- Introduce authentication and multi-user support
- Add analytics dashboards
- Add better matching between watch topics, content, outreach, and jobs

## Author

Built by Ichrak Ennaceur as an AI-powered career growth and networking platform.
