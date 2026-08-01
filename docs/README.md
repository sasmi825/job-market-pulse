# Documentation

Detailed documentation for Job Market Pulse. For setup, deployment and
maintenance, start with the [project README](../README.md).

| Document | What's in it |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System overview, component boundaries, data model, request lifecycle, deployment topology |
| [PIPELINE.md](PIPELINE.md) | Ingestion internals — scraping, cleaning, boilerplate detection, skill extraction, snapshots, known limitations |
| [API.md](API.md) | Full endpoint reference with real request/response examples and error cases |
| [DECISIONS.md](DECISIONS.md) | Why the code looks the way it does, and the bugs that shaped it |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Local setup, project layout, common tasks, conventions, gotchas |

## Where to start

**Understanding the system** → [ARCHITECTURE.md](ARCHITECTURE.md)

**Consuming the API** → [API.md](API.md)

**Changing extraction or scraping** → [PIPELINE.md](PIPELINE.md), then
[DEVELOPMENT.md](DEVELOPMENT.md#common-tasks)

**Wondering why something is written oddly** → [DECISIONS.md](DECISIONS.md).
Most of the non-obvious code exists because something failed silently, and the
reasoning is recorded there rather than lost.

## Live instance

| | |
|---|---|
| Dashboard | https://job-market-pulse-three.vercel.app |
| API | https://job-market-pulse.onrender.com |
| Interactive API docs | https://job-market-pulse.onrender.com/docs |

The backend is on a free tier and spins down after ~15 minutes idle — the first
request after a pause takes 30–50 seconds.
