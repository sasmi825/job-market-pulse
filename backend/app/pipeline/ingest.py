"""
Ingestion pipeline: scrape → extract skills → dedupe → store.
Can be run as a scheduled job or manually via API endpoint.
"""

import logging
from datetime import datetime, date

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.models import Job, Company, Skill, JobSkill, DailySnapshot
from app.scrapers import greenhouse, lever
from app.pipeline.skill_extractor import extract_skills, detect_seniority, detect_location_type
from app.pipeline.text_utils import (
    build_boilerplate_index,
    clean_for_extraction,
    clean_html,
)

logger = logging.getLogger(__name__)


async def run_full_pipeline(db: AsyncSession) -> dict:
    """Execute the full ingestion pipeline. Returns stats."""
    stats = {"scraped": 0, "new_jobs": 0, "updated": 0, "skills_linked": 0}

    # 1. Scrape all sources
    logger.info("Starting scrape...")
    results = [await greenhouse.scrape_all(), await lever.scrape_all()]

    raw_jobs = []
    for result in results:
        raw_jobs.extend(result.jobs)

    stats["scraped"] = len(raw_jobs)
    stats["sources"] = {r.source: r.summary() for r in results}
    # A source that yielded nothing while erroring is broken, not quiet. Every
    # Lever slug 404'd for weeks and the run still reported success.
    stats["sources_failed"] = sorted(r.source for r in results if r.is_broken)

    for result in results:
        if result.is_broken:
            logger.error(
                f"[{result.source}] SOURCE FAILED — 0 jobs from "
                f"{result.attempted} companies, all failed"
            )
        elif result.failed_companies:
            logger.warning(
                f"[{result.source}] {len(result.failed_companies)} of "
                f"{result.attempted} companies failed: {sorted(result.failed_companies)}"
            )

    logger.info(f"Scraped {len(raw_jobs)} total jobs")

    # 2. Learn each company's boilerplate before extracting anything. This
    # needs the whole corpus for a company, so it can't be done per job.
    boilerplate = _build_company_boilerplate(raw_jobs)
    stats["boilerplate_sentences"] = sum(len(v) for v in boilerplate.values())

    # 3. Process and store each job
    for raw in raw_jobs:
        try:
            result, skills_linked = await _process_single_job(
                db, raw, boilerplate.get(raw.get("company_name", ""), set())
            )
            stats["skills_linked"] += skills_linked
            if result == "new":
                stats["new_jobs"] += 1
            elif result == "updated":
                stats["updated"] += 1
        except Exception as e:
            logger.error(f"Error processing job {raw.get('external_id')}: {e}")
            # A failed flush poisons the session — without a rollback every
            # subsequent job fails too and the final commit raises.
            await db.rollback()
            continue

    await db.commit()

    # 4. Generate daily snapshot
    await _generate_snapshot(db)
    await db.commit()

    logger.info(f"Pipeline complete: {stats}")
    return stats


def _drop_employer_self_match(extracted: list[dict], company_name: str | None) -> list[dict]:
    """
    Drop a skill when it is just the employer's own name.

    Figma names itself throughout all 176 of its postings — in values
    statements, benefits copy and its careers email address — which made Figma
    the 4th most "in-demand" skill in the dataset. Those mentions are evidence
    of who is hiring, not of what they want. Unlike the repeated-sentence
    boilerplate this survives any frequency threshold, because the mentions are
    spread across dozens of different sentences.
    """
    if not company_name:
        return extracted
    employer = company_name.strip().lower()
    return [s for s in extracted if s["name"].strip().lower() != employer]


def _build_company_boilerplate(raw_jobs: list[dict]) -> dict[str, set[str]]:
    """Map each company to the sentences repeated across nearly all its postings."""
    by_company: dict[str, list[str]] = {}
    for raw in raw_jobs:
        company = raw.get("company_name") or ""
        by_company.setdefault(company, []).append(clean_html(raw.get("description")))

    index = {company: build_boilerplate_index(texts) for company, texts in by_company.items()}

    for company, sentences in index.items():
        if sentences:
            logger.info(
                f"[boilerplate] {company}: ignoring {len(sentences)} repeated "
                f"sentence(s) across {len(by_company[company])} postings"
            )
    return index


async def _process_single_job(
    db: AsyncSession, raw: dict, boilerplate: set[str] | None = None
) -> tuple[str, int]:
    """
    Process a single scraped job.
    Returns ('new' | 'updated' | 'skipped', number of skills linked).
    """

    # Ensure company exists
    company = await _get_or_create_company(db, raw["company_name"], raw.get("company_slug"))

    # Check if job already exists (dedupe by external_id + source)
    existing = await db.execute(
        select(Job).where(
            Job.external_id == raw["external_id"],
            Job.source == raw["source"],
        )
    )
    existing_job = existing.scalar_one_or_none()

    # Extract skills from description. The boards return escaped markup, so
    # strip it down to prose first — otherwise the extractor matches the tags
    # and "HTML" outranks every real skill.
    description = raw.get("description", "") or ""
    title = raw.get("title", "") or ""
    description_text = clean_for_extraction(description, boilerplate)
    combined_text = f"{title} {description_text}"

    extracted_skills = _drop_employer_self_match(
        extract_skills(combined_text), raw.get("company_name")
    )
    seniority = detect_seniority(title)
    location_type = detect_location_type(f"{raw.get('location', '')} {description_text}")

    if existing_job:
        # Update existing job
        existing_job.title = raw["title"]
        existing_job.location = raw.get("location")
        existing_job.salary_min = raw.get("salary_min")
        existing_job.salary_max = raw.get("salary_max")
        existing_job.description = description
        existing_job.seniority = seniority
        existing_job.location_type = location_type
        existing_job.scraped_at = datetime.utcnow()
        existing_job.is_active = True

        # Re-link skills
        linked = await _link_skills(db, existing_job, extracted_skills)
        return "updated", linked
    else:
        # Create new job
        job = Job(
            external_id=raw["external_id"],
            source=raw["source"],
            title=raw["title"],
            company_id=company.id,
            location=raw.get("location"),
            location_type=location_type,
            salary_min=raw.get("salary_min"),
            salary_max=raw.get("salary_max"),
            description=description,
            seniority=seniority,
            posted_at=raw.get("posted_at"),
            url=raw.get("url"),
        )
        db.add(job)
        await db.flush()  # get the job.id

        linked = await _link_skills(db, job, extracted_skills)
        return "new", linked


async def _get_or_create_company(db: AsyncSession, name: str, slug: str | None = None) -> Company:
    """Find or create a company record."""
    result = await db.execute(select(Company).where(Company.name == name))
    company = result.scalar_one_or_none()
    if not company:
        company = Company(name=name, careers_url=f"https://boards.greenhouse.io/{slug}" if slug else None)
        db.add(company)
        await db.flush()
    return company


async def _get_or_create_skill(db: AsyncSession, name: str, category: str) -> Skill:
    """Find or create a skill record."""
    result = await db.execute(select(Skill).where(Skill.name == name))
    skill = result.scalar_one_or_none()
    if not skill:
        skill = Skill(name=name, category=category)
        db.add(skill)
        await db.flush()
    return skill


async def _link_skills(db: AsyncSession, job: Job, extracted: list[dict]) -> int:
    """Create job-skill associations. Returns how many links were made."""
    # Clear existing links
    await db.execute(
        JobSkill.__table__.delete().where(JobSkill.job_id == job.id)
    )

    linked = 0
    for skill_data in extracted:
        skill = await _get_or_create_skill(db, skill_data["name"], skill_data["category"])
        link = JobSkill(job_id=job.id, skill_id=skill.id, confidence=skill_data["confidence"])
        db.add(link)
        linked += 1
    return linked


async def _generate_snapshot(db: AsyncSession):
    """Generate a daily aggregate snapshot."""
    today = date.today()

    # Check if we already have today's snapshot
    existing = await db.execute(
        select(DailySnapshot).where(DailySnapshot.snapshot_date == today)
    )
    if existing.scalar_one_or_none():
        return

    # Count active jobs
    total_result = await db.execute(
        select(func.count(Job.id)).where(Job.is_active == True)
    )
    total_jobs = total_result.scalar() or 0

    # Count jobs added today
    new_result = await db.execute(
        select(func.count(Job.id)).where(
            func.date(Job.scraped_at) == today
        )
    )
    new_jobs = new_result.scalar() or 0

    # Average salaries
    salary_result = await db.execute(
        select(
            func.avg(Job.salary_min),
            func.avg(Job.salary_max),
        ).where(Job.is_active == True, Job.salary_min.isnot(None))
    )
    row = salary_result.one()

    snapshot = DailySnapshot(
        snapshot_date=today,
        total_jobs=total_jobs,
        new_jobs=new_jobs,
        avg_salary_min=row[0],
        avg_salary_max=row[1],
    )
    db.add(snapshot)
