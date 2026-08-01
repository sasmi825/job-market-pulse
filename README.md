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
- **Frontend**: Next.js 14, Tailwind CSS, Recharts *(coming soon)*
- **Infra**: Docker Compose

## Quick Start

```bash
# 1. Clone and navigate
git clone <your-repo-url>
cd job-market-pulse

# 2. Copy env file
cp backend/.env.example backend/.env

# 3. Start services
docker compose up -d

# 4. Run the pipeline (scrape + process + store)
curl -X POST http://localhost:8000/api/v1/pipeline/run

# 5. Explore the API
open http://localhost:8000/docs
```

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/v1/jobs` | Paginated job listings with filters |
| `GET /api/v1/skills/top` | Skills ranked by demand |
| `GET /api/v1/companies/hiring` | Companies by open role count |
| `GET /api/v1/trends` | Daily time-series snapshots |
| `GET /api/v1/salaries` | Salary distribution by seniority |
| `POST /api/v1/pipeline/run` | Trigger ingestion pipeline |

## Data Sources

- **Greenhouse**: Public board API — no auth required
- **Lever**: Public postings API — no auth required
- More sources planned (Adzuna, Ashby, Workable)

## Project Status

- [x] Database schema and models
- [x] Greenhouse scraper
- [x] Lever scraper
- [x] Skill extraction pipeline
- [x] REST API with filters
- [ ] Frontend dashboard
- [ ] Scheduled pipeline (cron/APScheduler)
- [ ] Resume match score feature
- [ ] Deploy to Railway/Render
