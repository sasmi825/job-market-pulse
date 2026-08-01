#!/usr/bin/env python3
"""
Check every configured company slug against its job board.

Scraper configs are hand-maintained — neither Greenhouse nor Lever exposes a
directory endpoint — so slugs go stale silently as companies switch ATS. That
is exactly how Lever quietly contributed zero jobs while the pipeline kept
reporting success.

Usage (from backend/):
    python scripts/validate_slugs.py

Exit codes:
    0  every slug is live
    1  at least one slug is dead
"""

import asyncio
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import httpx

# Allow `python scripts/validate_slugs.py` from backend/ without installing.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.scrapers import greenhouse, lever  # noqa: E402

# A live board with almost nothing on it often means a migration in progress
# rather than a healthy quiet period — worth a look before it 404s outright.
LOW_COUNT_THRESHOLD = 3

REQUEST_TIMEOUT = 30.0
# Ping boards concurrently, but not so hard we look like an attack.
MAX_CONCURRENCY = 5

STATUS_OK = "ok"
STATUS_LOW = "low"
STATUS_DEAD = "dead"


@dataclass
class SlugCheck:
    source: str
    slug: str
    status: str
    jobs: int = 0
    detail: str = ""

    @property
    def marker(self) -> str:
        return {STATUS_OK: "OK", STATUS_LOW: "LOW", STATUS_DEAD: "DEAD"}[self.status]


async def _check(
    source: str,
    slug: str,
    fetch,
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
) -> SlugCheck:
    """Ping one slug using the scraper's own fetch function."""
    async with sem:
        try:
            jobs = await fetch(client, slug)
        except httpx.HTTPStatusError as e:
            return SlugCheck(source, slug, STATUS_DEAD, detail=f"HTTP {e.response.status_code}")
        except httpx.RequestError as e:
            return SlugCheck(source, slug, STATUS_DEAD, detail=f"network: {type(e).__name__}")
        except Exception as e:  # malformed payload, schema drift, …
            return SlugCheck(source, slug, STATUS_DEAD, detail=f"{type(e).__name__}: {e}")

    count = len(jobs)
    if count < LOW_COUNT_THRESHOLD:
        return SlugCheck(source, slug, STATUS_LOW, count, "possible board migration")
    return SlugCheck(source, slug, STATUS_OK, count)


async def validate() -> list[SlugCheck]:
    targets = [
        ("greenhouse", slug, greenhouse.fetch_company_jobs)
        for slug in greenhouse.GREENHOUSE_COMPANIES
    ] + [
        ("lever", slug, lever.fetch_company_jobs)
        for slug in lever.LEVER_COMPANIES
    ]

    sem = asyncio.Semaphore(MAX_CONCURRENCY)
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        return await asyncio.gather(
            *(_check(source, slug, fetch, client, sem) for source, slug, fetch in targets)
        )


def _render(results: list[SlugCheck]) -> None:
    slug_width = max([len(r.slug) for r in results] + [6])
    src_width = max([len(r.source) for r in results] + [6])

    header = f"{'SOURCE':<{src_width}}  {'SLUG':<{slug_width}}  {'STATUS':<6}  {'JOBS':>6}  DETAIL"
    print()
    print(header)
    print("-" * len(header))

    # Dead first, then low, then healthy — the actionable rows lead.
    order = {STATUS_DEAD: 0, STATUS_LOW: 1, STATUS_OK: 2}
    for r in sorted(results, key=lambda r: (order[r.status], r.source, r.slug)):
        jobs = str(r.jobs) if r.status != STATUS_DEAD else "-"
        print(
            f"{r.source:<{src_width}}  {r.slug:<{slug_width}}  "
            f"{r.marker:<6}  {jobs:>6}  {r.detail}"
        )

    print("-" * len(header))

    dead = [r for r in results if r.status == STATUS_DEAD]
    low = [r for r in results if r.status == STATUS_LOW]
    total_jobs = sum(r.jobs for r in results)

    by_source: dict[str, int] = {}
    for r in results:
        by_source[r.source] = by_source.get(r.source, 0) + r.jobs

    breakdown = ", ".join(f"{src} {n:,}" for src, n in sorted(by_source.items()))
    print(
        f"{len(results)} slugs checked  |  {len(results) - len(dead)} live, "
        f"{len(dead)} dead, {len(low)} low  |  {total_jobs:,} jobs ({breakdown})"
    )

    if dead:
        print(f"\nDEAD — remove or replace: {', '.join(f'{r.source}/{r.slug}' for r in dead)}")
    if low:
        print(f"LOW  — worth a manual check: {', '.join(f'{r.source}/{r.slug}' for r in low)}")
    if not dead and not low:
        print("\nAll configured slugs are live and healthy.")


def main() -> int:
    # The scrapers log per-company info; keep the table readable.
    logging.disable(logging.INFO)

    results = asyncio.run(validate())
    _render(results)
    return 1 if any(r.status == STATUS_DEAD for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
