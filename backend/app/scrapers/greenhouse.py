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
from app.scrapers.base import ScrapeResult

logger = logging.getLogger(__name__)

# Companies to scrape — add more as you discover them
# Find slugs at: https://boards.greenhouse.io/{slug}
# notion, plaid, anduril, ramp and rippling were removed — all five 404 now,
# having moved off Greenhouse. Slugs need periodic revalidation; the pipeline
# reports per-company failures in its stats so this stays visible.
GREENHOUSE_COMPANIES = [
    "airbnb",
    "stripe",
    "figma",
    "discord",
    "coinbase",
    "netlify",
    "gusto",
    "brex",
    "verkada",
    "faire",
]

BASE_URL = "https://boards-api.greenhouse.io/v1/boards"


async def fetch_company_jobs(client: httpx.AsyncClient, company_slug: str) -> list[dict]:
    """
    Fetch all jobs for a single Greenhouse company.

    Raises on failure so the caller can tell a dead board apart from one with
    no current openings.
    """
    url = f"{BASE_URL}/{company_slug}/jobs"
    resp = await client.get(url, params={"content": "true"})
    resp.raise_for_status()
    data = resp.json()
    jobs = data.get("jobs", [])
    logger.info(f"[greenhouse] {company_slug}: found {len(jobs)} jobs")
    return [_normalize_job(job, company_slug) for job in jobs]


def _normalize_job(raw: dict, company_slug: str) -> dict:
    """Transform raw Greenhouse JSON into our internal schema."""
    # `or {}` rather than a .get default: these keys are often present but
    # null, and a default only applies when the key is missing entirely.
    location = (raw.get("location") or {}).get("name", "")

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
    # Greenhouse sometimes puts pay range in metadata. Stripe, Figma and
    # Netlify send `"metadata": null`, which the old `.get("metadata", [])`
    # turned into `for field in None` — a TypeError that the caller's blanket
    # except swallowed, silently dropping all 728 of their postings.
    for field in raw.get("metadata") or []:
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
        "discord": "Discord",
        "coinbase": "Coinbase",
        "netlify": "Netlify",
        "gusto": "Gusto",
        "brex": "Brex",
        "verkada": "Verkada",
        "faire": "Faire",
    }
    return name_overrides.get(slug, slug.replace("-", " ").title())


async def scrape_all() -> ScrapeResult:
    """Scrape all configured Greenhouse companies, recording per-company failures."""
    result = ScrapeResult(source="greenhouse", attempted=len(GREENHOUSE_COMPANIES))

    async with httpx.AsyncClient(timeout=30.0) as client:
        for slug in GREENHOUSE_COMPANIES:
            try:
                jobs = await fetch_company_jobs(client, slug)
            except httpx.HTTPStatusError as e:
                logger.warning(f"[greenhouse] {slug}: HTTP {e.response.status_code}")
                result.failed_companies.append(slug)
                continue
            except Exception as e:
                logger.error(f"[greenhouse] {slug}: {e}")
                result.failed_companies.append(slug)
                continue

            if jobs:
                result.jobs.extend(jobs)
            else:
                result.empty_companies.append(slug)

    logger.info(
        f"[greenhouse] total scraped: {len(result.jobs)} jobs "
        f"({len(result.failed_companies)} of {result.attempted} companies failed)"
    )
    return result
