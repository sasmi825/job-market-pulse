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

## Deployment

Backend on Railway, dashboard on Vercel.

**Backend (Railway)**

1. New project → Deploy from GitHub repo → set the service **Root Directory** to
   `backend`. The Dockerfile is detected via `backend/railway.json`.
2. Add the **PostgreSQL** and **Redis** plugins. Both inject their connection
   URLs automatically; `postgres://` is rewritten to `postgresql+asyncpg://` at
   startup, so no manual editing is needed.
3. Set these service variables:

   | Variable | Value |
   |---|---|
   | `ENVIRONMENT` | `production` |
   | `PIPELINE_TOKEN` | a long random string (see below) |
   | `CORS_ORIGINS` | your Vercel URL, e.g. `https://job-market-pulse.vercel.app` |

   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

4. Generate a public domain for the service and note the URL.

The app **refuses to boot** in production if `DATABASE_URL` still contains the
development password or if `PIPELINE_TOKEN` is unset — a loud failure beats a
publicly-triggerable scraper.

**Frontend (Vercel)**

1. Import the same repo → set **Root Directory** to `frontend`.
2. Set `NEXT_PUBLIC_API_URL` to `https://<your-railway-domain>/api/v1`.
   This is inlined at build time, so it must be set *before* the first build;
   changing it later needs a redeploy, not just a restart.
3. Deploy, then add the resulting domain to `CORS_ORIGINS` on Railway.

**Seeding data after deploy** — the pipeline is manual-trigger, so a fresh
deployment has an empty database until you run:

```bash
curl -X POST https://<your-railway-domain>/api/v1/pipeline/run \
  -H "X-Pipeline-Token: $PIPELINE_TOKEN"
```

A full run scrapes 19 boards and takes several minutes.

## Known Limitations & Next Steps

**Data coverage is inherently fragile.** This project scrapes public job board APIs that companies control and can change without notice — 5 of 12 Lever companies and 5 of 15 Greenhouse companies had gone stale during development. `validate_slugs.py` catches this proactively now, but a scheduled CI job (rather than manual runs) is the natural next step.

**Skill extraction is keyword-based, not semantic.** ~65% of jobs return zero matched skills — mostly genuinely non-technical roles or postings that describe requirements in prose without naming tools, plus some real taxonomy gaps. A more complete fix would move toward NLP-based extraction (spaCy or an LLM-based extractor).

**Company boilerplate required active mitigation.** Repeated company text (client lists, self-descriptions) initially produced misleading rankings — one company's self-description alone put "Agentic AI" at #3 overall. A boilerplate-detection step now strips repeated sentences before extraction, but it's a heuristic, not a guarantee, on new sources.

**Non-English postings aren't filtered.** Some sources return non-English descriptions the English-only taxonomy can't parse, which register indistinguishably from genuinely skill-less postings. Language detection is a planned improvement.

**Resume matching is v1.** It reuses the same keyword taxonomy as job extraction, so it inherits the same blind spots — no semantic understanding, no weighting by how central a skill is to a role.

**Salary data is incomplete.** Only ~27% of postings include parseable salary information, since disclosure depends entirely on what each company chooses to include in the posting text.

## Project Status

- [x] Database schema and models
- [x] Greenhouse scraper
- [x] Lever scraper
- [x] Skill extraction pipeline
- [x] REST API with filters
- [x] Frontend dashboard
- [ ] Scheduled pipeline (cron/APScheduler)
- [x] Resume match score feature
- [ ] Scheduled slug validation (CI)
- [ ] Deploy to Railway/Render
