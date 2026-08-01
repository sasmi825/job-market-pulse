# Job Market Pulse 📊

Real-time job market analytics dashboard that tracks skill demand, salary trends, and hiring volume across top tech companies.

## Architecture

```
Data Sources (Greenhouse, Lever)
        ↓
  Ingestion Service (Python scrapers, scheduled cron)
        ↓
  Processing Pipeline (skill extraction, deduplication, normalization)
        ↓
  Storage (PostgreSQL + Redis cache)
        ↓
  FastAPI Backend (REST endpoints + aggregation queries)
        ↓
  Next.js Dashboard (charts, filters, trends, search)
```

## Tech Stack

- **Backend**: FastAPI (Python 3.12)
- **Database**: PostgreSQL 16 + Redis 7
- **Pipeline**: Custom scrapers + keyword-based skill extraction
- **Frontend**: Next.js 14 (App Router), TypeScript, Tailwind CSS, hand-rolled SVG charts
- **Infra**: Docker Compose

## Quick Start

```bash
# 1. Clone and navigate
git clone <your-repo-url>
cd job-market-pulse

# 2. Copy env file
cp backend/.env.example backend/.env

# 3. Start services
docker-compose up -d

# 4. Run the pipeline (scrape + process + store)
curl -X POST http://localhost:8000/api/v1/pipeline/run

# 5. Explore the API
open http://localhost:8000/docs

# 6. Start the dashboard
cd frontend && npm install && npm run dev
open http://localhost:3000
```

### Local environment notes

- **`docker compose` vs `docker-compose`** — this machine has the standalone
  `docker-compose` binary, not the Docker CLI plugin, so the hyphenated form is
  required. `docker compose` fails with `unknown command`.
- **npm version warning** — npm 11.6.2 is installed against Node 20.10.0, and
  npm prints `npm v11.6.2 does not support Node.js v20.10.0` on every command.
  It is cosmetic: installs, builds and scripts all work. Silence it by moving
  to Node 22 (`nvm install 22`) or pinning `npm@10`. Left alone deliberately.
- **Don't run `next build` while `next dev` is running** — they share
  `frontend/.next`, and the build leaves the dev server serving 500s with
  `MODULE_NOT_FOUND`. Fix: stop the dev server, `rm -rf .next`, restart.

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/v1/jobs` | Paginated job listings with filters |
| `GET /api/v1/skills/top` | Skills ranked by demand |
| `GET /api/v1/companies/hiring` | Companies by open role count |
| `GET /api/v1/trends` | Daily time-series snapshots |
| `GET /api/v1/salaries` | Salary distribution by seniority |
| `POST /api/v1/resume/analyze` | Score a PDF/txt resume against current demand |
| `POST /api/v1/pipeline/run` | Trigger ingestion pipeline |

## Data Sources

- **Greenhouse**: Public board API — no auth required (10 companies)
- **Lever**: Public postings API — no auth required (9 companies)
- More sources planned (Adzuna, Ashby, Workable)

Neither API has a directory endpoint, so company slugs are hand-maintained and
go stale as companies switch ATS. The pipeline reports per-company failures in
its response (`stats.sources`) and flags a wholly dead source in
`stats.sources_failed`, so silent half-coverage is visible rather than assumed.

## Maintenance

Run `python backend/scripts/validate_slugs.py` periodically to catch stale
company slugs before they silently degrade coverage. This is a known limitation
of hand-maintained scraper configs; a scheduled CI job is a natural next step.

The script pings every configured Greenhouse and Lever slug, prints a summary
table, and exits non-zero if any slug is dead — so it can be dropped into CI
unchanged. Live boards returning fewer than 3 jobs are flagged `LOW`, since a
near-empty board usually means a migration in progress rather than a clean 404.

```
SOURCE      SLUG        STATUS    JOBS  DETAIL
greenhouse  stripe      OK         548
greenhouse  netlify     OK           4
lever       veeva       OK         786
----------------------------------------------
19 slugs checked  |  19 live, 0 dead, 0 low  |  3,801 jobs
```

## Project Status

- [x] Database schema and models
- [x] Greenhouse scraper
- [x] Lever scraper
- [x] Skill extraction pipeline
- [x] REST API with filters
- [x] Frontend dashboard
- [ ] Scheduled pipeline (cron/APScheduler)
- [x] Resume match score feature
- [ ] Deploy to Railway/Render
