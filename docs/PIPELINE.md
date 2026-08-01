# The ingestion pipeline

What happens between "a company posts a job" and "a number appears on the
dashboard" — and the failure modes that shaped each stage.

Entry point: `run_full_pipeline()` in
[`backend/app/pipeline/ingest.py`](../backend/app/pipeline/ingest.py).

---

## Stages

```
1. Scrape        both sources, per-company failures recorded
2. Learn         per-company boilerplate index (needs whole corpus)
3. Process       per job: clean -> extract -> upsert -> link skills
4. Commit
5. Snapshot      one aggregate row per calendar day
```

A run takes roughly **5 minutes** and currently yields ~3,800 postings from 19
companies across 2 sources.

---

## 1. Scrape

Two scrapers, same contract: given a client and a company slug, return a list
of normalised dicts.

| Source | Endpoint | Companies |
|---|---|---|
| Greenhouse | `boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true` | 10 |
| Lever | `api.lever.co/v0/postings/{slug}` | 9 |

Both are public and unauthenticated. **Neither has a directory endpoint**, so
slugs are hand-maintained and go stale as companies switch ATS.

### Failures are data, not noise

`fetch_company_jobs` **raises** on failure. `scrape_all` catches per company and
records the outcome in a `ScrapeResult`:

```python
@dataclass
class ScrapeResult:
    source: str
    jobs: list[dict]
    failed_companies: list[str]   # 404, network error, bad payload
    empty_companies: list[str]    # responded fine, no openings
    attempted: int
```

The distinction matters. Both used to return `[]`, which made a dead board
indistinguishable from a quiet one — and that is precisely how **every Lever
slug 404'd for weeks while the pipeline reported success**. Those results surface
in the response as `stats.sources` and `stats.sources_failed`.

### Normalisation

Each scraper maps its source's shape onto a common dict: `external_id`,
`source`, `title`, `company_name`, `company_slug`, `location`, `description`,
`salary_min`, `salary_max`, `posted_at`, `url`.

Two source-specific quirks handled here:

- **Greenhouse timestamps are timezone-aware**; `posted_at` is
  `TIMESTAMP WITHOUT TIME ZONE`. They are converted to naive UTC, matching Lever
  and `scraped_at`. Without this, asyncpg rejects the insert outright.
- **Null-valued keys.** Several fields arrive as `"metadata": null` rather than
  absent, so `.get("metadata", [])` returns `None` and iterating raises. Every
  such access uses `or []` / `or {}` instead. See
  [DECISIONS.md](DECISIONS.md#the-728-job-silent-data-loss).

### Salary extraction

Greenhouse exposes a `metadata` array that *can* hold a pay range, but most
boards leave it empty — so extraction falls back to scanning the cleaned
description for a dollar range:

```
$120,000 - $180,000     $120K to $180K     $95,000 — $140,000
```

Both figures must be present and ≥ $10,000, which rejects stipends, hourly
rates and equity figures. Coverage is about **27% of postings**; the rest simply
don't publish a range.

> **Known gap:** currency is not validated. A posting quoting TWD with a bare
> `$` parses as USD — two Taiwan roles land at ~$2.4M and inflate the `ceiling`
> column in `/salaries`. Averages are effectively unaffected.

---

## 2. Learn company boilerplate

Before any extraction, the pipeline groups postings by company and finds
sentences repeated **verbatim across ≥60% of that company's postings** (minimum
8 postings, sentences ≥40 characters).

This exists because company marketing copy is repeated on every posting and
poisons skill counts:

| Boilerplate | Effect before |
|---|---|
| Verkada's *"uses our agentic AI to deter theft"* × 275 postings | **Agentic AI ranked #3 skill overall** |
| Coinbase's AI-usage policy paragraph × 111 postings | 159 of 202 "Generative AI" matches |
| Brex's customer list naming Zoom, Plaid, Reddit × 302 postings | Zoom looked like a required skill |

A per-term blocklist would be endless whack-a-mole and would also suppress
genuine mentions. Detecting the *shape* of the problem generalises.

The 60% threshold is deliberate. Real requirements vary by role — even a very
technical company posts sales, finance and legal roles — so a sentence
reproduced verbatim across most postings is company copy, not a requirement.
Verified that engineering skills survived at the affected companies (Coinbase
kept Go 36, AWS 28, Python 22).

---

## 3. Process each job

### Clean

`clean_for_extraction()` runs three steps:

1. **Unescape twice.** Boards return escaped markup (`&lt;div&gt;`), and
   entities *inside* those tags arrive double-escaped (`&amp;mdash;`). One pass
   leaves literal `&mdash;` in the prose — and leaves salary ranges unparseable,
   because the dash between the figures never resolves.
2. **Strip tags**, collapse whitespace.
3. **Drop boilerplate** — customer-name lists (by shape) and the per-company
   repeated sentences from stage 2.

Customer-list detection requires a cue phrase (`including`, `trusted by`,
`customers include`, …) plus a run of ≥3 comma-separated proper nouns — but
**never drops a sentence containing a tracked skill**. Without that guard,
*"tooling including Python, Docker, and Kubernetes"* matches the same shape as a
customer list and gets deleted.

### Extract

`extract_skills()` matches a curated taxonomy of ~100 terms across 8 categories:
language, framework, tool, cloud, database, data, practice, business, ai.

Most terms match case-insensitively on word boundaries. **Ambiguous terms get
context-sensitive patterns against the original casing:**

| Term | Problem | Rule |
|---|---|---|
| `Go` | the English verb | requires `Golang`, `goroutines`, `Go programming/developer`, `in/with/using Go`, adjacency to another language, or `(Go)` in a title |
| `Excel` | *"excel in this role"* | case-sensitive, negative lookahead on `in`/`at`/`as`/`with` |
| `LLM` | the law degree | negative lookahead on `degree`/`program`/`candidates` |

Before this, `Go` ranked #2 overall with 259 matches — top hits included
*"Associate Counsel, Innovation and Thought Leadership"* and
*"Manager, Guest Services"*. It now sits at ~113, all genuine.

Seniority and location type are inferred from title and text by keyword.

### Store

Lookup by `(external_id, source)`:

- **Found** → update fields, refresh `scraped_at`, set `is_active`, re-link skills
- **Not found** → insert, `flush()` to obtain the id, link skills

Skills matching the **employer's own name** are dropped. Figma names itself in
all 176 of its postings — in values statements, benefits copy, and its careers
email address — which made Figma the 4th most "in-demand" skill. Those mentions
indicate who is hiring, not what they want, and they're spread across dozens of
distinct sentences so no frequency threshold catches them.

### Error handling

Each job is processed in a `try`, and a failure triggers `await db.rollback()`
before continuing. Without the rollback the session is poisoned: every
subsequent job fails and the final commit raises `PendingRollbackError`. One bad
row used to kill an entire run.

> **Trade-off:** rollback discards the whole uncommitted batch, not just the
> failing row. No row has failed since the timezone fix, but a mid-run failure
> would cost that run's work.

---

## 4. Snapshot

One `daily_snapshots` row per calendar day, capturing totals and averages. The
generator **returns early if today's row exists**, so re-running the pipeline
does not add a second point — the trend chart needs two calendar days before it
can draw a line.

---

## Output

```json
{
  "scraped": 3801,
  "new_jobs": 0,
  "updated": 3801,
  "skills_linked": 3888,
  "sources": {
    "greenhouse": {"jobs": 1849, "companies_attempted": 10, "companies_failed": [], "companies_empty": []},
    "lever":      {"jobs": 1952, "companies_attempted": 9,  "companies_failed": [], "companies_empty": []}
  },
  "sources_failed": [],
  "boilerplate_sentences": 218
}
```

`new=0 / updated=3801` on a re-run is the signal that it reached an already-
seeded database.

---

## Known limitations

**~65% of postings extract zero skills.** Investigated in detail; three distinct
causes:

1. **Genuinely non-technical roles** (the majority) — sales, marketing, legal,
   finance, support. They ask for competencies, not tools.
2. **Taxonomy gaps** (~32% of the zero-skill set) — Salesforce alone appears in
   21% of them.
3. **Concept-level phrasing** — Airbnb's ML roles ask for *"ML engineering
   experience"* and *"Agentic AI products"* without naming a single framework.
   Nothing for a keyword matcher to find.

It is not a text-quality problem: zero-skill postings average 8,382 characters
versus 8,296 for postings that do match.

**Non-English postings** are not filtered and register identically to
skill-less ones.

**Keyword matching has no semantics.** A posting saying "no Python required"
scores Python. Moving to NLP or LLM-based extraction is the real fix.

---

## Operations

| Task | How |
|---|---|
| Scheduled run | GitHub Actions, daily 06:00 UTC |
| Manual run | Actions tab → *Daily pipeline* → **Run workflow** |
| Manual run (local) | `API_URL=... PIPELINE_TOKEN=... python backend/scripts/trigger_pipeline.py` |
| Check slug health | `python backend/scripts/validate_slugs.py` |

`validate_slugs.py` pings every configured slug, prints a table, flags boards
under 3 jobs as `LOW` (usually a migration in progress), and exits non-zero if
any slug is dead.
