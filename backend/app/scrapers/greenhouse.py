"""
Greenhouse public job board scraper.

Every company using Greenhouse exposes jobs at:
  https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs

No auth required. Returns JSON with all active postings.
"""

import logging
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

# Companies to scrape — add more as you discover them
# Find slugs at: https://boards.greenhouse.io/{slug}
GREENHOUSE_COMPANIES = [
    "airbnb",
    "stripe",
    "figma",
    "notion",
    "discord",
    "coinbase",
    "netlify",
    "gusto",
    "brex",
    "plaid",
    "verkada",
    "anduril",
    "ramp",
    "rippling",
    "faire",
]

BASE_URL = "https://boards-api.greenhouse.io/v1/boards"


async def fetch_company_jobs(client: httpx.AsyncClient, company_slug: str) -> list[dict]:
    """Fetch all jobs for a single Greenhouse company."""
    url = f"{BASE_URL}/{company_slug}/jobs"
    try:
        resp = await client.get(url, params={"content": "true"})
        resp.raise_for_status()
        data = resp.json()
        jobs = data.get("jobs", [])
        logger.info(f"[greenhouse] {company_slug}: found {len(jobs)} jobs")
        return [_normalize_job(job, company_slug) for job in jobs]
    except httpx.HTTPStatusError as e:
        logger.warning(f"[greenhouse] {company_slug}: HTTP {e.response.status_code}")
        return []
    except Exception as e:
        logger.error(f"[greenhouse] {company_slug}: {e}")
        return []


def _normalize_job(raw: dict, company_slug: str) -> dict:
    """Transform raw Greenhouse JSON into our internal schema."""
    location = raw.get("location", {}).get("name", "")

    # Parse salary from metadata if present
    salary_min, salary_max = _extract_salary(raw)

    return {
        "external_id": str(raw["id"]),
        "source": "greenhouse",
        "title": raw.get("title", ""),
        "company_name": _slug_to_name(company_slug),
        "company_slug": company_slug,
        "location": location,
        "description": raw.get("content", ""),
        "salary_min": salary_min,
        "salary_max": salary_max,
        "posted_at": _parse_date(raw.get("updated_at")),
        "url": raw.get("absolute_url", ""),
    }


def _extract_salary(raw: dict) -> tuple[float | None, float | None]:
    """Try to pull salary from Greenhouse metadata fields."""
    # Greenhouse sometimes puts pay range in metadata
    for field in raw.get("metadata", []):
        name = (field.get("name") or "").lower()
        value = field.get("value") or ""
        if any(kw in name for kw in ["salary", "compensation", "pay"]):
            return _parse_salary_range(str(value))
    return None, None


def _parse_salary_range(text: str) -> tuple[float | None, float | None]:
    """Extract min/max salary from text like '$120,000 - $180,000'."""
    import re
    numbers = re.findall(r'[\$]?\s*([\d,]+(?:\.\d+)?)', text)
    if len(numbers) >= 2:
        try:
            low = float(numbers[0].replace(",", ""))
            high = float(numbers[1].replace(",", ""))
            # Filter out unreasonable values (hourly rates, etc.)
            if low > 10000 and high > 10000:
                return low, high
        except ValueError:
            pass
    elif len(numbers) == 1:
        try:
            val = float(numbers[0].replace(",", ""))
            if val > 10000:
                return val, val
        except ValueError:
            pass
    return None, None


def _parse_date(date_str: str | None) -> datetime | None:
    if not date_str:
        return None
    try:
        parsed = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    # Greenhouse returns tz-aware timestamps, but posted_at is TIMESTAMP
    # WITHOUT TIME ZONE — normalize to naive UTC like the other sources.
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _slug_to_name(slug: str) -> str:
    """Convert 'airbnb' to 'Airbnb'."""
    name_overrides = {
        "airbnb": "Airbnb",
        "stripe": "Stripe",
        "figma": "Figma",
        "notion": "Notion",
        "discord": "Discord",
        "coinbase": "Coinbase",
        "netlify": "Netlify",
        "gusto": "Gusto",
        "brex": "Brex",
        "plaid": "Plaid",
        "verkada": "Verkada",
        "anduril": "Anduril",
        "ramp": "Ramp",
        "rippling": "Rippling",
        "faire": "Faire",
    }
    return name_overrides.get(slug, slug.replace("-", " ").title())


async def scrape_all() -> list[dict]:
    """Scrape all configured Greenhouse companies."""
    all_jobs = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        for slug in GREENHOUSE_COMPANIES:
            jobs = await fetch_company_jobs(client, slug)
            all_jobs.extend(jobs)
    logger.info(f"[greenhouse] total scraped: {len(all_jobs)} jobs")
    return all_jobs
