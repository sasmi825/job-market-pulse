# Engineering decisions

Why the code looks the way it does. Most entries exist because something broke
in a way that wasn't obvious, and the fix encodes what was learned.

---

## Silent failure was the recurring theme

Four separate bugs shared one shape: **something failed, and the system reported
success.** They're worth reading together, because the pattern matters more than
any individual fix.

### The 728-job silent data loss

Stripe, Figma and Netlify return `"metadata": null` in their Greenhouse
payloads. The code did:

```python
for field in raw.get("metadata", []):
```

A `.get()` default applies only when the key is **absent** — not when its value
is `null`. So this evaluated to `for field in None` and raised `TypeError`,
which the caller's blanket `except` swallowed and logged as a per-company
warning. Three healthy boards reported zero jobs. **728 postings, 39% of
Greenhouse coverage, vanished without an error.**

Fix: `raw.get("metadata") or []`, applied to every null-prone access.

**Lesson:** with third-party JSON, `or []` is not equivalent to a `.get()`
default, and the difference is invisible until it isn't.

### Lever returned nothing for weeks

All 12 configured Lever slugs 404'd — the companies had migrated off Lever. The
scraper caught each error, logged a warning, returned `[]`, and the pipeline
reported a successful run. Coverage silently halved to one source.

The root cause wasn't the 404s; it was that `[]` meant both *"this board is
dead"* and *"this company has no openings"*. Scrapers now return a
`ScrapeResult` distinguishing the two, and the pipeline surfaces
`stats.sources_failed`.

**Lesson:** an empty result and a failure must not share a representation.

### One bad row killed the whole run

Greenhouse returns timezone-aware timestamps; `posted_at` is `TIMESTAMP WITHOUT
TIME ZONE`. asyncpg rejected the first such insert — and because the failed
flush poisons the SQLAlchemy session, **every subsequent job also failed**, and
the final commit raised `PendingRollbackError`. A single bad row turned into a
total run failure.

Two fixes: normalise timestamps to naive UTC at the scraper boundary, and
`await db.rollback()` in the per-job error handler so the session recovers.

### `sslmode` would have killed the deploy

Render's External Database URL ends in `?sslmode=require`. SQLAlchemy passes
unknown query params through to the driver, and asyncpg doesn't accept that
keyword:

```
TypeError: connect() got an unexpected keyword argument 'sslmode'
```

The app would have died at boot, before serving a request. Caught by testing
provider URL formats rather than assuming they were interchangeable.

Fix: `sslmode` is **renamed** to `ssl` (asyncpg's spelling, same values) rather
than dropped — dropping it would silently downgrade a connection meant to be
encrypted.

---

## Skill extraction: precision over recall

### Ambiguous terms need context, not blocklists

`Go` originally ranked **#2 with 259 matches**. Its top hits were *"Associate
Counsel, Innovation and Thought Leadership"* and *"Manager, Guest Services"* —
the extractor was matching the English verb.

The fix is a case-sensitive contextual pattern requiring a language signal:
`Golang`, `goroutines`, `Go programming/developer`, `in/with/using Go`,
adjacency to another language, or `(Go)` in a title. Demand fell to ~113, all
genuine.

The same treatment was needed for `Excel` (*"excel in this role"*) and `LLM`
(the law degree — these postings include legal roles).

**Why not a blocklist:** it can't distinguish *"we use Go"* from *"go to
market"*. Only context can.

### Company boilerplate needed three different mechanisms

Repeated company copy inflated skill counts, and each variant defeated the
previous fix:

| Pattern | Example | Mechanism |
|---|---|---|
| Customer-name lists | Brex names Zoom, Plaid, Reddit in all 302 postings | Shape detection: cue phrase + ≥3 comma-separated proper nouns |
| Repeated marketing copy | Verkada's *"our agentic AI"* in all 275 postings | Sentences repeated verbatim across ≥60% of a company's postings |
| Employer self-reference | Figma names itself in all 176 postings | Drop skills matching the employer's name |

The third resisted the second: Figma's mentions are spread across dozens of
*different* sentences ("At Figma we celebrate…", "accommodations-ext@figma.com"),
none individually frequent enough to trip a threshold.

**Before:** Agentic AI ranked #3 overall and Figma #4 — both artifacts of
marketing copy.

Two guards keep this from over-reaching:

- Customer-list detection **never drops a sentence containing a tracked skill**.
  *"tooling including Python, Docker, and Kubernetes"* has the identical shape
  to a customer list, and an earlier version deleted it.
- The 60% threshold was validated by confirming engineering skills survived at
  the affected companies (Coinbase kept Go 36, AWS 28, Python 22).

### Accepting a worse-looking metric

Zero-skill postings rose from 55% to 65% after this work. That is the correct
outcome: the removed matches were false positives. Precision improved while the
headline number got worse.

Worth stating plainly, because the instinct is to optimise the visible metric.

---

## HTML must be unescaped twice

Descriptions arrive escaped (`&lt;div&gt;`), but entities *inside* those tags
were escaped before that, arriving as `&amp;mdash;`. One unescape pass leaves
literal `&mdash;` in the prose.

This wasn't cosmetic. Salary ranges are `$120,000 &amp;mdash; $180,000`, and the
separator never resolved to a dash — so **zero of 1,122 postings had a parseable
salary** and `/salaries` returned an empty array. Fixing the double-unescape
took coverage to ~27%.

Before this, `HTML` was the **#1 ranked skill** with 279 matches, purely from
matching `&lt;html&gt;` in markup.

---

## API design

### `search` matches title OR skill, via `EXISTS`

The UI offers one "skill or title" box, so the backend has to OR them. The
obvious implementation joins `job_skills` — but a job matching three skills
returns three rows and **inflates `total`**. An `EXISTS` subquery keeps one row
per job.

### `/skills/top` returns `total` separately

`limit` caps the array at 50, so a caller counting `skills` to answer "how many
skills do we track" got 50 when the real answer was 83. The count is now
explicit and independent of pagination.

### The pipeline endpoint is authenticated

A run fans out to 19 external boards and takes ~5 minutes. Left open on a public
URL that's both a self-inflicted DoS and a fast route to an IP ban from
Greenhouse and Lever.

`X-Pipeline-Token` is required in production — the app **refuses to start**
without one. Locally the token may be unset and the endpoint stays open, so the
documented quick-start `curl` still works.

---

## Deployment

### Fail loudly on misconfiguration

Production refuses to boot if `DATABASE_URL` still carries the development
password, or if `PIPELINE_TOKEN` is unset. A crash with a specific message beats
a service that silently runs against the wrong database or exposes an open
scraper trigger.

The credential check matches on the **password**, not the whole URL. An earlier
version compared against the exact localhost default and waved through the
docker-compose variant (`@db:5432`) — same password, different host.

### GitHub Actions over Render Cron

Render's Cron Job service is a paid add-on; GitHub-hosted runners are free for
public repositories. The scheduled run lives in
[`.github/workflows/daily-pipeline.yml`](../.github/workflows/daily-pipeline.yml).

It deliberately **does not treat HTTP 200 as success**: a source returning no
jobs fails the run, and dead company slugs surface as warnings. Given Lever's
history of 200-with-nothing, a bare `curl` exit code would have been useless.

### The trigger script avoids curl

`backend/scripts/trigger_pipeline.py` exists because `python:3.12-slim` ships
with neither curl nor wget — a curl command inside the backend image fails with
`curl: not found`. Using the standard library avoids an apt layer for one HTTP
call.

---

## Frontend

### Design tokens ported verbatim

`lib/theme.ts` reproduces the prototype's `THEMES` object exactly, oklch values
unchanged, so the built UI matches the design rather than approximating it.

One deliberate deviation: the prototype's CSS listed the system font *before*
IBM Plex Sans, meaning it never actually rendered in Plex on a Mac. Plex leads
in the implementation, matching the stated typography.

### Real data broke assumptions the mock never tested

| Assumption in the design | Reality |
|---|---|
| Hardcoded "Stripe, Airbnb, Netflix and 22 others" | Those companies aren't all in the dataset — copy is now derived from the live leaderboard |
| A trend line always has points | Only one snapshot exists at first; the chart states why instead of rendering a broken line |
| Every job has 3–5 skills | ~65% have none — the column shows `—` |
| Salary bands scale to floor/ceiling | A TWD posting parsing as $2.4M would squash every real band; bands scale to averages |
| The table renders all matches | Only the first 50 — the count now reads "Showing 50 of 3,801" |

### All fetches live in `lib/api.ts`

No component calls `fetch`. This keeps loading and error handling uniform and
request shapes in one place. Search debounces at 350ms — typing ten characters
issues one request.

---

## Known gaps

Documented rather than fixed, with the reasoning:

| Gap | Why it's open |
|---|---|
| No automated tests | The highest-value next task. Every bug above was found by hand and could regress. |
| ~65% zero-skill extraction | Needs semantic extraction (spaCy/LLM), not more keywords. |
| No currency validation | TWD parses as USD; affects `floor`/`ceiling` only, ~2 of 1,018 ranges. |
| `/resume/analyze` unrated | Public, CPU-bound PDF parsing on a 512MB instance. |
| No language filtering | Non-English postings register as skill-less. |
| Slug lists hand-maintained | `validate_slugs.py` detects rot; scheduling it is the next step. |
| No migrations | `create_all` at startup handles additive changes only. |
| Rollback discards the batch | A mid-run failure costs that run's work, not just the bad row. |
