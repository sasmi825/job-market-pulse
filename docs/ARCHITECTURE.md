# Architecture

How the system fits together, what each piece owns, and why the boundaries sit
where they do.

For setup and deployment, see the [README](../README.md). For the ingestion
internals, see [PIPELINE.md](PIPELINE.md).

---

## System overview

```
┌─────────────────────────────────────────────────────────────────┐
│  GitHub Actions (daily 06:00 UTC)                               │
│  .github/workflows/daily-pipeline.yml                           │
└───────────────────────────┬─────────────────────────────────────┘
                            │ POST /api/v1/pipeline/run
                            │ X-Pipeline-Token
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  FastAPI backend (Render, Docker)                               │
│                                                                 │
│   app/api/routes.py ──── read endpoints + pipeline trigger      │
│           │                                                     │
│           ├── app/pipeline/ingest.py    orchestration           │
│           │        ├── app/scrapers/    Greenhouse, Lever       │
│           │        ├── text_utils.py    cleaning, boilerplate   │
│           │        └── skill_extractor  taxonomy matching       │
│           │                                                     │
│           └── app/models/models.py ──── SQLAlchemy ORM          │
└───────────────────────────┬─────────────────────────────────────┘
                            │ asyncpg
                            ▼
                 ┌──────────────────────┐
                 │  PostgreSQL (Render) │
                 └──────────────────────┘
                            ▲
                            │ REST/JSON over CORS
┌───────────────────────────┴─────────────────────────────────────┐
│  Next.js 14 dashboard (Vercel)                                  │
│                                                                 │
│   app/page.tsx ──── state, data fetching, composition           │
│           ├── lib/api.ts       every fetch lives here           │
│           ├── lib/theme.ts     design tokens (light/dark)       │
│           └── components/      9 presentational sections        │
└─────────────────────────────────────────────────────────────────┘
```

External dependencies: `boards-api.greenhouse.io` and `api.lever.co`, both
public and unauthenticated.

---

## Why the pieces are split this way

**The scrapers know nothing about the database.** `greenhouse.py` and
`lever.py` return plain dicts in a shared shape. They don't import models or a
session. This keeps them independently testable and means adding a third source
requires no changes to ingestion logic beyond one line.

**Skill extraction is pure.** `skill_extractor.py` takes a string and returns a
list of dicts. No I/O, no database, no config. Every extraction rule can be
verified in isolation — which matters, because the ambiguous-term handling
(`Go`, `Excel`, `LLM`) is subtle and easy to regress.

**Text cleaning is separate from extraction.** `text_utils.py` handles the
mechanics of turning escaped job-board HTML into prose and stripping company
boilerplate. Extraction assumes it receives clean text. Merging the two would
make both harder to reason about, and the boilerplate detection needs a whole
company's corpus while extraction is per-job.

**All frontend network access is in `lib/api.ts`.** Components receive data as
props and render it. No component calls `fetch`. This makes loading and error
states uniform and keeps request shapes in one place.

---

## Data model

Five tables. `Job` is the centre; everything else hangs off it.

```
companies                      skills
  id          UUID PK            id        UUID PK
  name        UNIQUE             name      UNIQUE
  industry                       category
  size_bucket                       │
  careers_url                       │
  created_at                        │
      │                             │
      │ 1:N                         │
      ▼                             │
jobs                                │
  id             UUID PK            │
  external_id    ─┐                 │
  source         ─┴ UNIQUE together │
  title                             │
  company_id     FK ────────────────┼──┐
  location                          │  │
  location_type   remote|hybrid|onsite │
  salary_min / salary_max              │
  salary_currency                      │
  description     raw escaped HTML     │
  seniority       intern..staff        │
  posted_at / scraped_at               │
  url                                  │
  is_active                            │
      │                                │
      │ 1:N                            │
      ▼                                ▼
job_skills
  job_id    FK PK ──── ON DELETE CASCADE
  skill_id  FK PK
  confidence  FLOAT

daily_snapshots          (standalone aggregate)
  id             UUID PK
  snapshot_date  UNIQUE — at most one row per calendar day
  total_jobs / new_jobs
  avg_salary_min / avg_salary_max
  top_skills / top_companies / top_locations   JSON
  created_at
```

### Design notes

**`UNIQUE (external_id, source)`** is the deduplication key. The same posting
re-scraped tomorrow updates its row rather than inserting a duplicate. Sources
are namespaced because IDs are only unique within a board.

**`description` stores the raw escaped HTML** as the source returned it.
Cleaning happens at extraction time, not on write. The raw text is preserved
so extraction rules can change without re-scraping — but it does mean the
stored column is markup, not prose.

**`job_skills.confidence`** is populated (0.5–1.0, scaled by mention count) but
nothing currently reads it. It exists for future ranking.

**`daily_snapshots.snapshot_date` is UNIQUE**, and the generator returns early
if today's row exists. Running the pipeline twice in one day does not produce
two points — which is why the trend chart needs two calendar days before it can
draw a line.

**Schema is created by `Base.metadata.create_all` at startup**, not migrations.
Fine for additive changes on a single deployment; a destructive change would
need Alembic (it is already a dependency, unconfigured).

---

## Request lifecycle

### A read (`GET /api/v1/jobs`)

1. Browser → Vercel-served bundle → `lib/api.ts` → Render.
2. CORS middleware checks `Origin` against `CORS_ORIGINS`.
3. `get_db()` yields an `AsyncSession` per request.
4. Query builds with `joinedload(company)` + `selectinload(skills)` — two
   queries total, no N+1.
5. Filters compose as `WHERE` clauses; `search` matches title **OR** skill via
   `EXISTS` (a join would multiply rows and inflate `total`).
6. Count runs against the filtered subquery, then a paginated fetch.

### A pipeline run

See [PIPELINE.md](PIPELINE.md). In short: token check → scrape both sources →
build per-company boilerplate index → process each job → commit → snapshot.

---

## Frontend composition

`app/page.tsx` is the only stateful component. It owns theme, date range,
filters, and all fetched data, and passes everything down as props.

Three independent fetch groups, so a slow or failing one doesn't block the rest:

| Group | Triggers on | Feeds |
|---|---|---|
| Range-scoped | date range change | top skills, trends |
| Overview | mount | metric cards, companies, salary bands |
| Jobs | filter/search change (debounced 350ms) | roles table |

The range group uses `Promise.allSettled` so a failing trends call still lets
skills render. Search debounces at 350ms — typing ten characters issues one
request.

Every fetch is cancellation-guarded with a `cancelled` flag so a slow in-flight
response can't overwrite fresher state.

---

## Deployment topology

| Component | Host | Tier | Notes |
|---|---|---|---|
| Backend | Render Web Service (Docker) | Free | Spins down after ~15 min idle |
| Database | Render Postgres | Free | **Expires ~30 days** |
| Frontend | Vercel | Hobby | Static + client rendering |
| Scheduler | GitHub Actions | Free (public repo) | Daily 06:00 UTC |

Nothing requires a paid tier. The two consequences worth remembering: a 30–50s
cold start on the first request after idle, and a hard expiry date on the
database ([re-seeding procedure](../README.md#re-seeding-after-the-free-database-expires)).

`NEXT_PUBLIC_API_URL` is inlined into the frontend bundle at **build** time, so
changing the backend URL requires a Vercel redeploy, not just a restart.
