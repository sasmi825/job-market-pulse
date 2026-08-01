"""
Lever public job board scraper.

Every company using Lever exposes jobs at:
  https://api.lever.co/v0/postings/{company_slug}

No auth required. Returns JSON array of postings.
"""

import logging
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

LEVER_COMPANIES = [
    "netflix",
    "twitch",
    "databricks",
    "cloudflare",
    "github",
    "vercel",
    "linear",
    "supabase",
    "planetscale",
    "retool",
    "loom",
    "dbt-labs",
]

BASE_URL = "https://api.lever.co/v0/postings"


async def fetch_company_jobs(client: httpx.AsyncClient, company_slug: str) -> list[dict]:
    """Fetch all jobs for a single Lever company."""
    url = f"{BASE_URL}/{company_slug}"
    try:
        resp = await client.get(url)
        resp.raise_for_status()
        postings = resp.json()
        if not isinstance(postings, list):
            return []
        logger.info(f"[lever] {company_slug}: found {len(postings)} jobs")
        return [_normalize_job(p, company_slug) for p in postings]
    except httpx.HTTPStatusError as e:
        logger.warning(f"[lever] {company_slug}: HTTP {e.response.status_code}")
        return []
    except Exception as e:
        logger.error(f"[lever] {company_slug}: {e}")
        return []


def _normalize_job(raw: dict, company_slug: str) -> dict:
    """Transform raw Lever JSON into our internal schema."""
    categories = raw.get("categories", {})
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
        "netflix": "Netflix",
        "twitch": "Twitch",
        "databricks": "Databricks",
        "cloudflare": "Cloudflare",
        "github": "GitHub",
        "vercel": "Vercel",
        "linear": "Linear",
        "supabase": "Supabase",
        "planetscale": "PlanetScale",
        "retool": "Retool",
        "loom": "Loom",
        "dbt-labs": "dbt Labs",
    }
    return name_overrides.get(slug, slug.replace("-", " ").title())


async def scrape_all() -> list[dict]:
    """Scrape all configured Lever companies."""
    all_jobs = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        for slug in LEVER_COMPANIES:
            jobs = await fetch_company_jobs(client, slug)
            all_jobs.extend(jobs)
    logger.info(f"[lever] total scraped: {len(all_jobs)} jobs")
    return all_jobs
