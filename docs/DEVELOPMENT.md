# Development guide

Working on the project locally.

---

## Prerequisites

| Tool | Notes |
|---|---|
| Docker + `docker-compose` | This machine has the **standalone binary**, not the CLI plugin — `docker compose` (spaced) fails with `unknown command` |
| Node 18.17+ | Frontend. Node 20.10 is installed here |
| Python 3.12 | Only needed to run the helper scripts on the host |

---

## First run

```bash
cp backend/.env.example backend/.env
docker-compose up -d                      # postgres, redis, api
curl -X POST http://localhost:8000/api/v1/pipeline/run   # ~5 min
```

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev                               # http://localhost:3000
```

Tables are created automatically at startup. `PIPELINE_TOKEN` may be left unset
locally — the trigger endpoint stays open against localhost.

---

## Layout

```
backend/
  app/
    api/routes.py        all HTTP endpoints
    core/config.py       settings, DSN normalisation, production guards
    core/database.py     async engine + session factory
    models/models.py     SQLAlchemy ORM
    pipeline/
      ingest.py          orchestration
      skill_extractor.py taxonomy matching (pure)
      text_utils.py      HTML cleaning, boilerplate detection (pure)
      resume.py          PDF/txt text extraction (pure)
    scrapers/
      base.py            ScrapeResult
      greenhouse.py      Greenhouse board API
      lever.py           Lever postings API
  scripts/
    validate_slugs.py    check configured slugs are alive
    trigger_pipeline.py  trigger a run against a deployed API

frontend/
  app/page.tsx           all state and data fetching
  lib/api.ts             every network call
  lib/theme.ts           design tokens (light/dark)
  components/            9 presentational sections
```

---

## Common tasks

### Adding a company

Append the slug to `GREENHOUSE_COMPANIES` or `LEVER_COMPANIES` and add a display
name to that scraper's `name_overrides`. Verify it first — neither API has a
directory endpoint, and a wrong slug 404s:

```bash
curl -s -o /dev/null -w "%{http_code}\n" \
  "https://boards-api.greenhouse.io/v1/boards/<slug>/jobs"
curl -s "https://api.lever.co/v0/postings/<slug>" | head -c 200
```

Then confirm with `python backend/scripts/validate_slugs.py`.

### Adding a skill

Add the canonical name to the right category in `SKILL_TAXONOMY`.

**If the term is also an ordinary English word, add a contextual pattern to
`_AMBIGUOUS_PATTERNS`** — otherwise it will produce noise. `Go` reached #2
overall by matching the verb before it was guarded. Test both directions:

```python
from app.pipeline.skill_extractor import extract_skills
extract_skills("We use Go and Rust")            # should match
extract_skills("Go to market strategy lead")    # should not
```

### Changing the schema

`create_all` only adds missing tables — it will not alter existing ones. For a
destructive change locally:

```bash
docker-compose down -v && docker-compose up -d   # wipes the volume
```

Alembic is a dependency but unconfigured; a production schema change needs it.

---

## Verifying changes

There is **no automated test suite yet** — the highest-value outstanding task.
Until then, verify by hand.

### Pure functions (fast, no containers)

```bash
cd backend
python3 -c "
import sys; sys.path.insert(0,'.')
from app.pipeline.text_utils import clean_for_extraction
from app.pipeline.skill_extractor import extract_skills
t = clean_for_extraction('&lt;p&gt;We use Python and Go&lt;/p&gt;')
print(t, [s['name'] for s in extract_skills(t)])
"
```

### Config guards

```bash
docker-compose exec -T api python -c "
from app.core.config import Settings
Settings(environment='production', pipeline_token='x'*32)  # should raise
"
```

### Full pipeline

```bash
curl -X POST http://localhost:8000/api/v1/pipeline/run | python3 -m json.tool
```

Check `sources_failed` is empty and each source's `companies_failed` is empty.

### Frontend

```bash
cd frontend
node_modules/.bin/tsc --noEmit     # typecheck
npm run build                      # production build
```

> **Don't run `next build` while `next dev` is running.** They share
> `frontend/.next`, and the build leaves the dev server serving 500s with
> `MODULE_NOT_FOUND`. Recover with: stop dev server, `rm -rf .next`, restart.

---

## Conventions

**Scrapers return dicts, never model instances.** They must not import models or
a session.

**Extraction and cleaning stay pure.** No I/O in `skill_extractor.py`,
`text_utils.py`, or `resume.py` — it's what makes them verifiable in one line.

**Distinguish empty from failed.** A source with no openings and a dead source
must not return the same value. This is the bug that hid Lever's outage for
weeks.

**Comment the non-obvious, not the obvious.** The codebase explains *why*
`or []` differs from a `.get()` default, not what a for-loop does.

**Components don't fetch.** All network access goes through `lib/api.ts`.

---

## Gotchas

| Symptom | Cause |
|---|---|
| `docker compose: unknown command` | Use hyphenated `docker-compose` |
| `npm warn ... does not support Node.js v20.10.0` | Cosmetic. npm 11 wants Node ≥20.17 |
| Dev server 500s with `MODULE_NOT_FOUND` | `next build` ran while `next dev` was live |
| Frontend shows "Can't reach the API" | Backend down, or origin missing from `CORS_ORIGINS` |
| Deployed API changes ignored by frontend | `NEXT_PUBLIC_API_URL` is inlined at build time — needs a redeploy |
| Trend chart shows a placeholder | Fewer than 2 daily snapshots; needs two calendar days |
| Pipeline returns 200 but nothing changed | Check `sources_failed` — 200 does not mean healthy |

---

## Deployment

See the [README](../README.md#deployment).

Both services redeploy automatically on a push to `main`.

**Vercel** requires **Root Directory = `frontend`** under *Settings → General*.
The project was originally created with `vercel link` from inside `frontend/`,
which recorded the root as `.` — correct for a CLI upload of that directory, but
wrong once Git integration builds from the repository root, where there is no
`package.json`.

To deploy the frontend manually (bypassing Git):

```bash
cd frontend && vercel --prod
```
