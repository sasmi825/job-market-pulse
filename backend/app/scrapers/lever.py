"""
Lever public job board scraper.

Every company using Lever exposes jobs at:
  https://api.lever.co/v0/postings/{company_slug}

No auth required. Returns JSON array of postings.
"""

import logging
from datetime import datetime

import httpx

from app.scrapers.base import ScrapeResult

logger = logging.getLogger(__name__)

# Every slug in the original list (netflix, github, vercel, databricks, …) now
# 404s — those companies moved off Lever. The v0 API itself is fine; there is
# just no directory endpoint, so slugs have to be verified by hand. Each of
# these was confirmed to return postings before being added.
LEVER_COMPANIES = [
    "veeva",
    "lyrahealth",
    "shieldai",
    "matchgroup",
    "ro",
    "anchorage",
    "neon",
    "tala",
    "alloy",
]

BASE_URL = "https://api.lever.co/v0/postings"


async def fetch_company_jobs(client: httpx.AsyncClient, company_slug: str) -> list[dict]:
    """
    Fetch all jobs for a single Lever company.

    Raises on failure so the caller can distinguish a dead slug from a company
    that simply has no openings — both used to return [].
    """
    url = f"{BASE_URL}/{company_slug}"
    resp = await client.get(url)
    resp.raise_for_status()
    postings = resp.json()
    if not isinstance(postings, list):
        raise ValueError(f"expected a list of postings, got {type(postings).__name__}")
    logger.info(f"[lever] {company_slug}: found {len(postings)} jobs")
    return [_normalize_job(p, company_slug) for p in postings]


def _normalize_job(raw: dict, company_slug: str) -> dict:
    """Transform raw Lever JSON into our internal schema."""
    # `or {}` — the key is often present but null, which a .get default misses.
    categories = raw.get("categories") or {}
    location = categories.get("location", "") or ""
    salary_min, salary_max = _extract_salary(raw)

    return {
        "external_id": raw.get("id", ""),
        "source": "lever",
        "title": raw.get("text", ""),
        "company_name": _slug_to_name(company_slug),
        "company_slug": company_slug,
        "location": location,
        "description": raw.get("descriptionPlain", "") or raw.get("description", ""),
        "salary_min": salary_min,
        "salary_max": salary_max,
        "posted_at": _parse_timestamp(raw.get("createdAt")),
        "url": raw.get("hostedUrl", ""),
    }


def _extract_salary(raw: dict) -> tuple[float | None, float | None]:
    """Try to pull salary from Lever's additional fields."""
    additional = raw.get("additional", "") or ""
    description = raw.get("descriptionPlain", "") or ""
    combined = f"{additional} {description}"

    import re
    patterns = [
        r'\$\s*([\d,]+(?:k)?)\s*[-–to]+\s*\$?\s*([\d,]+(?:k)?)',
    ]
    for pattern in patterns:
        match = re.search(pattern, combined, re.IGNORECASE)
        if match:
            low = _parse_salary_value(match.group(1))
            high = _parse_salary_value(match.group(2))
            if low and high and low > 10000 and high > 10000:
                return low, high
    return None, None


def _parse_salary_value(val: str) -> float | None:
    try:
        val = val.replace(",", "").strip()
        if val.lower().endswith("k"):
            return float(val[:-1]) * 1000
        return float(val)
    except ValueError:
        return None


def _parse_timestamp(ts: int | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.utcfromtimestamp(ts / 1000)
    except (ValueError, TypeError, OSError):
        return None


def _slug_to_name(slug: str) -> str:
    name_overrides = {
        "veeva": "Veeva Systems",
        "lyrahealth": "Lyra Health",
        "shieldai": "Shield AI",
        "matchgroup": "Match Group",
        "ro": "Ro",
        "anchorage": "Anchorage Digital",
        "neon": "Neon",
        "tala": "Tala",
        "alloy": "Alloy",
    }
    return name_overrides.get(slug, slug.replace("-", " ").title())


async def scrape_all() -> ScrapeResult:
    """Scrape all configured Lever companies, recording per-company failures."""
    result = ScrapeResult(source="lever", attempted=len(LEVER_COMPANIES))

    async with httpx.AsyncClient(timeout=30.0) as client:
        for slug in LEVER_COMPANIES:
            try:
                jobs = await fetch_company_jobs(client, slug)
            except httpx.HTTPStatusError as e:
                logger.warning(f"[lever] {slug}: HTTP {e.response.status_code}")
                result.failed_companies.append(slug)
                continue
            except Exception as e:
                logger.error(f"[lever] {slug}: {e}")
                result.failed_companies.append(slug)
                continue

            if jobs:
                result.jobs.extend(jobs)
            else:
                result.empty_companies.append(slug)

    logger.info(
        f"[lever] total scraped: {len(result.jobs)} jobs "
        f"({len(result.failed_companies)} of {result.attempted} companies failed)"
    )
    return result
