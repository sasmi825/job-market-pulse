"""
Greenhouse public job board scraper.

Every company using Greenhouse exposes jobs at:
  https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs

No auth required. Returns JSON with all active postings.
"""

import logging
import re
from datetime import datetime, timezone

import httpx

from app.pipeline.text_utils import clean_html

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
    """Pull a salary range from Greenhouse metadata, falling back to the description."""
    # Greenhouse sometimes puts pay range in metadata
    for field in raw.get("metadata", []):
        name = (field.get("name") or "").lower()
        value = field.get("value") or ""
        if any(kw in name for kw in ["salary", "compensation", "pay"]):
            low, high = _parse_salary_range(str(value))
            if low is not None:
                return low, high

    # Most boards leave metadata empty and put the range in the posting body.
    return _parse_salary_from_text(clean_html(raw.get("content", "")))


# "$120,000 - $180,000", "$120,000 — $180,000", "$120K to $180K"
_SALARY_RANGE_RE = re.compile(
    r"\$\s*([\d,]+(?:\.\d+)?\s*[kK]?)"
    r"\s*(?:-|–|—|to|through)\s*"
    r"\$?\s*([\d,]+(?:\.\d+)?\s*[kK]?)"
)


def _parse_salary_from_text(text: str) -> tuple[float | None, float | None]:
    """Scan prose for a dollar-denominated pay range."""
    if not text:
        return None, None

    for match in _SALARY_RANGE_RE.finditer(text):
        low = _parse_salary_value(match.group(1))
        high = _parse_salary_value(match.group(2))
        # Guard against equity grants, hourly rates and stray dollar figures.
        if low and high and low >= 10000 and high >= low:
            return low, high
    return None, None


def _parse_salary_value(val: str) -> float | None:
    """Parse '120,000' or '120K' into a float."""
    try:
        val = val.replace(",", "").strip()
        if val.lower().endswith("k"):
            return float(val[:-1].strip()) * 1000
        return float(val)
    except ValueError:
        return None


def _parse_salary_range(text: str) -> tuple[float | None, float | None]:
    """Extract min/max salary from text like '$120,000 - $180,000'."""
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
