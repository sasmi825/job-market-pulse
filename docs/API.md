# API reference

Base URL (deployed): `https://job-market-pulse.onrender.com/api/v1`
Local: `http://localhost:8000/api/v1`

Interactive docs: [`/docs`](https://job-market-pulse.onrender.com/docs) (Swagger UI).

All responses are JSON. Read endpoints are unauthenticated;
`POST /pipeline/run` requires a token.

> **Cold start:** on the free tier the service spins down after ~15 minutes
> idle. The first request then takes **30–50 seconds**. Subsequent requests are
> fast (~100ms).

Examples below are real responses from the deployed instance.

---

## `GET /health`

Liveness probe. Used as Render's health check.

```json
{ "status": "ok" }
```

---

## `GET /api/v1/jobs`

Paginated job listings with filters.

| Param | Type | Default | Notes |
|---|---|---|---|
| `search` | string | — | Matches title **OR** skill name (case-insensitive, partial) |
| `location` | string | — | Partial match on location text |
| `location_type` | string | — | `remote` \| `hybrid` \| `onsite` |
| `seniority` | string | — | `intern` \| `junior` \| `mid` \| `senior` \| `lead` \| `staff` |
| `source` | string | — | `greenhouse` \| `lever` |
| `skill` | string | — | Partial match on a linked skill name |
| `limit` | int | 50 | Max 200 |
| `offset` | int | 0 | |

Results are ordered by `posted_at` descending and restricted to `is_active`.

```bash
curl "https://job-market-pulse.onrender.com/api/v1/jobs?seniority=senior&limit=1"
```

```json
{
  "total": 731,
  "limit": 1,
  "offset": 0,
  "jobs": [
    {
      "id": "391a4021-bcf6-4a4f-9697-5784518ee0e2",
      "title": "Senior Counsel, Product",
      "company": "Coinbase",
      "location": "Remote - USA",
      "location_type": "remote",
      "seniority": "senior",
      "salary_min": 224995.0,
      "salary_max": 264700.0,
      "source": "greenhouse",
      "posted_at": "2026-08-01T08:09:26",
      "url": "https://www.coinbase.com/careers/positions/8069582?gh_jid=8069582",
      "skills": []
    }
  ]
}
```

**`total` is the count of all matches, not the page size.** Filters compose with
AND; `search` is the only one that ORs internally (title or skill), implemented
with `EXISTS` so matching multiple skills can't inflate the count.

**`skills` is often empty** — about 65% of postings extract none. See
[PIPELINE.md](PIPELINE.md#known-limitations).

**`salary_min`/`salary_max` are null for ~73% of postings**, since disclosure
depends on what each company chooses to publish.

---

## `GET /api/v1/skills/top`

Skills ranked by how many active postings mention them.

| Param | Type | Default | Notes |
|---|---|---|---|
| `category` | string | — | `language`, `framework`, `tool`, `cloud`, `database`, `data`, `practice`, `business`, `ai` |
| `limit` | int | 20 | Max 50 |
| `days` | int | 30 | Max 90; window on `scraped_at` |

```json
{
  "total": 100,
  "period_days": 30,
  "skills": [
    { "name": "SQL",    "category": "language", "demand": 322 },
    { "name": "Python", "category": "language", "demand": 309 }
  ]
}
```

**`total` is the distinct skill count in the window, independent of `limit`.**
It exists because `limit` caps the array at 50, so counting `skills` under-reports
— a caller doing that reported 50 when the real figure was 83.

---

## `GET /api/v1/companies/hiring`

Companies ranked by active posting count.

| Param | Type | Default | Notes |
|---|---|---|---|
| `limit` | int | 15 | Max 50 |

```json
{
  "companies": [
    { "name": "Veeva Systems", "open_roles": 786 },
    { "name": "Stripe",        "open_roles": 548 },
    { "name": "Lyra Health",   "open_roles": 515 }
  ]
}
```

---

## `GET /api/v1/trends`

Daily aggregate snapshots for time-series charts.

| Param | Type | Default | Notes |
|---|---|---|---|
| `days` | int | 30 | Max 90 |

```json
{
  "period_days": 30,
  "snapshots": [
    {
      "date": "2026-08-01",
      "total_jobs": 3801,
      "new_jobs": 3801,
      "avg_salary_min": null,
      "avg_salary_max": null,
      "top_skills": null
    }
  ]
}
```

**At most one snapshot exists per calendar day.** Running the pipeline twice in
a day does not produce a second point, so a freshly seeded deployment returns a
single snapshot until the next day's run.

---

## `GET /api/v1/salaries`

Salary distribution grouped by seniority. Only postings with a parsed
`salary_min` are included.

| Param | Type | Notes |
|---|---|---|
| `seniority` | string | Restrict to one level |
| `skill` | string | Restrict to postings linked to a matching skill |

```json
{
  "buckets": [
    {
      "seniority": "senior",
      "count": 268,
      "avg_min": 180187.0,
      "avg_max": 233270.0,
      "floor": 82500.0,
      "ceiling": 2438889.0
    }
  ]
}
```

> **`floor` and `ceiling` are raw extremes and can be misleading.** Currency
> isn't validated, so a posting quoting TWD with a bare `$` parses as USD — the
> 2,438,889 above is one such role. `avg_min`/`avg_max` are robust; the
> dashboard scales its bars to those rather than the extremes.

---

## `POST /api/v1/resume/analyze`

Scores a resume against current skill demand. **Stateless** — the file is parsed
in memory and never written to disk or the database.

**Request:** `multipart/form-data` with a `file` field. Accepts `.pdf` or
`.txt`, max 5 MB.

```bash
curl -X POST https://job-market-pulse.onrender.com/api/v1/resume/analyze \
  -F "file=@resume.pdf"
```

```json
{
  "score": 30,
  "matched_skills": ["SQL", "Python", "AWS", "React", "TypeScript", "CI/CD"],
  "missing_skills": ["Salesforce", "LLM", "R", "Machine Learning", "Java"],
  "resume_skills_found": ["AWS", "Airflow", "CI/CD", "Docker", "Python", "..."]
}
```

`score` = matched ÷ 20, as a percentage. The comparison set is the **top 20
in-demand skills over the last 30 days** — deliberately small, so the score
isn't diluted by rare skills. It uses the same extractor and the same
aggregation as `/skills/top`, so resume and job skills come from one taxonomy.

`resume_skills_found` is everything detected in the resume, including skills
outside the top-20 comparison set.

### Errors

| Status | Detail | Cause |
|---|---|---|
| 400 | `Unsupported file type — upload a PDF or .txt file.` | Wrong extension |
| 400 | `The uploaded file is empty.` | Zero bytes |
| 400 | `File is too large — please upload a resume under 5 MB.` | > 5 MB |
| 400 | `Couldn't read any text from that file...` | Scanned/image-only PDF |
| 400 | `That PDF couldn't be read — it may be corrupt or encrypted.` | Malformed PDF |
| 503 | `No skill demand data yet — run the ingestion pipeline first.` | Empty database |

> **Not rate-limited.** PDF parsing is CPU-bound and this endpoint is public and
> unauthenticated — a known gap on a 512MB instance.

---

## `POST /api/v1/pipeline/run`

Triggers a full ingestion run. **Requires authentication.**

**Header:** `X-Pipeline-Token: <token>`

```bash
curl -X POST https://job-market-pulse.onrender.com/api/v1/pipeline/run \
  -H "X-Pipeline-Token: $PIPELINE_TOKEN"
```

```json
{
  "status": "complete",
  "stats": {
    "scraped": 3801,
    "new_jobs": 0,
    "updated": 3801,
    "skills_linked": 3888,
    "sources": {
      "greenhouse": { "jobs": 1849, "companies_attempted": 10, "companies_failed": [], "companies_empty": [] },
      "lever":      { "jobs": 1952, "companies_attempted": 9,  "companies_failed": [], "companies_empty": [] }
    },
    "sources_failed": [],
    "boilerplate_sentences": 218
  }
}
```

| Status | Meaning |
|---|---|
| 200 | Run completed — **inspect `sources_failed` before assuming success** |
| 401 | Missing or invalid `X-Pipeline-Token` |

**A 200 does not mean healthy.** `sources_failed` lists sources that returned
nothing at all, and each source's `companies_failed` lists dead slugs. Every
Lever slug 404'd for weeks while this endpoint returned 200. The
[GitHub Actions workflow](../.github/workflows/daily-pipeline.yml) fails the run
on a dead source and warns on dead companies.

**Runs synchronously and takes ~5 minutes.** Clients need a generous timeout;
the scheduled workflow allows 900 seconds.

Locally, `PIPELINE_TOKEN` may be unset and the endpoint stays open. In
production the app **refuses to start** without one.

---

## CORS

Browser origins are allowlisted via `CORS_ORIGINS` (comma-separated). Requests
from other origins receive no `Access-Control-Allow-Origin` header and are
blocked by the browser.

Vercel preview deployments get unique URLs and are **not** allowlisted — only
the production alias is. That's intentional.
