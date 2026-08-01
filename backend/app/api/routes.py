from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File
from sqlalchemy import select, func, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.database import get_db
from app.models.models import Job, Company, Skill, JobSkill, DailySnapshot
from app.pipeline.ingest import run_full_pipeline
from app.pipeline.resume import extract_resume_text, ResumeParseError
from app.pipeline.skill_extractor import extract_skills

router = APIRouter()


# ──────────────────────────────────────────────
# Jobs
# ──────────────────────────────────────────────

@router.get("/jobs")
async def list_jobs(
    db: AsyncSession = Depends(get_db),
    search: Optional[str] = None,
    location: Optional[str] = None,
    location_type: Optional[str] = None,
    seniority: Optional[str] = None,
    source: Optional[str] = None,
    skill: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
):
    """List jobs with filters."""
    query = (
        select(Job)
        .options(joinedload(Job.company), selectinload(Job.skills).joinedload(JobSkill.skill))
        .where(Job.is_active == True)
        .order_by(desc(Job.posted_at))
    )

    if search:
        # The UI offers one box for "skill or title", so match either. EXISTS
        # rather than a join keeps one row per job — a join would multiply rows
        # by matching skills and inflate the total count.
        skill_match = (
            select(JobSkill.job_id)
            .join(Skill, Skill.id == JobSkill.skill_id)
            .where(JobSkill.job_id == Job.id, Skill.name.ilike(f"%{search}%"))
            .exists()
        )
        query = query.where(or_(Job.title.ilike(f"%{search}%"), skill_match))
    if location:
        query = query.where(Job.location.ilike(f"%{location}%"))
    if location_type:
        query = query.where(Job.location_type == location_type)
    if seniority:
        query = query.where(Job.seniority == seniority)
    if source:
        query = query.where(Job.source == source)
    if skill:
        query = query.join(JobSkill).join(Skill).where(Skill.name.ilike(f"%{skill}%"))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Get paginated results
    result = await db.execute(query.offset(offset).limit(limit))
    jobs = result.unique().scalars().all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "jobs": [
            {
                "id": str(j.id),
                "title": j.title,
                "company": j.company.name if j.company else None,
                "location": j.location,
                "location_type": j.location_type,
                "seniority": j.seniority,
                "salary_min": j.salary_min,
                "salary_max": j.salary_max,
                "source": j.source,
                "posted_at": j.posted_at.isoformat() if j.posted_at else None,
                "url": j.url,
                "skills": [js.skill.name for js in j.skills if js.skill],
            }
            for j in jobs
        ],
    }


# ──────────────────────────────────────────────
# Skills (demand ranking)
# ──────────────────────────────────────────────

async def _skill_demand_rows(
    db: AsyncSession,
    limit: int,
    days: int,
    category: Optional[str] = None,
):
    """
    Skills ranked by how many active postings mention them.
    Shared by /skills/top and the resume matcher so both score against the
    same definition of "in demand".
    """
    cutoff = datetime.utcnow() - timedelta(days=days)

    query = (
        select(Skill.name, Skill.category, func.count(JobSkill.job_id).label("demand"))
        .join(JobSkill, Skill.id == JobSkill.skill_id)
        .join(Job, Job.id == JobSkill.job_id)
        .where(Job.is_active == True, Job.scraped_at >= cutoff)
    )

    if category:
        query = query.where(Skill.category == category)

    query = query.group_by(Skill.name, Skill.category).order_by(desc("demand")).limit(limit)

    result = await db.execute(query)
    return result.all()


@router.get("/skills/top")
async def top_skills(
    db: AsyncSession = Depends(get_db),
    category: Optional[str] = None,
    limit: int = Query(default=20, le=50),
    days: int = Query(default=30, le=90),
):
    """Top skills by demand (number of job postings mentioning them)."""
    rows = await _skill_demand_rows(db, limit=limit, days=days, category=category)

    # Callers that want "how many skills do we track" can't infer it from the
    # returned list, since `limit` caps it at 50.
    cutoff = datetime.utcnow() - timedelta(days=days)
    total_query = (
        select(func.count(func.distinct(Skill.id)))
        .select_from(Skill)
        .join(JobSkill, Skill.id == JobSkill.skill_id)
        .join(Job, Job.id == JobSkill.job_id)
        .where(Job.is_active == True, Job.scraped_at >= cutoff)
    )
    if category:
        total_query = total_query.where(Skill.category == category)
    total = (await db.execute(total_query)).scalar() or 0

    return {
        "total": total,
        "period_days": days,
        "skills": [
            {"name": r.name, "category": r.category, "demand": r.demand}
            for r in rows
        ],
    }


# ──────────────────────────────────────────────
# Companies (hiring volume)
# ──────────────────────────────────────────────

@router.get("/companies/hiring")
async def companies_hiring(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=15, le=50),
):
    """Companies ranked by number of active job postings."""
    query = (
        select(Company.name, func.count(Job.id).label("open_roles"))
        .join(Job, Company.id == Job.company_id)
        .where(Job.is_active == True)
        .group_by(Company.name)
        .order_by(desc("open_roles"))
        .limit(limit)
    )

    result = await db.execute(query)
    rows = result.all()

    return {
        "companies": [
            {"name": r.name, "open_roles": r.open_roles}
            for r in rows
        ],
    }


# ──────────────────────────────────────────────
# Trends (time-series)
# ──────────────────────────────────────────────

@router.get("/trends")
async def get_trends(
    db: AsyncSession = Depends(get_db),
    days: int = Query(default=30, le=90),
):
    """Daily snapshot trends for charts."""
    cutoff = datetime.utcnow().date() - timedelta(days=days)

    result = await db.execute(
        select(DailySnapshot)
        .where(DailySnapshot.snapshot_date >= cutoff)
        .order_by(DailySnapshot.snapshot_date)
    )
    snapshots = result.scalars().all()

    return {
        "period_days": days,
        "snapshots": [
            {
                "date": s.snapshot_date.isoformat(),
                "total_jobs": s.total_jobs,
                "new_jobs": s.new_jobs,
                "avg_salary_min": s.avg_salary_min,
                "avg_salary_max": s.avg_salary_max,
                "top_skills": s.top_skills,
            }
            for s in snapshots
        ],
    }


# ──────────────────────────────────────────────
# Salary distribution
# ──────────────────────────────────────────────

@router.get("/salaries")
async def salary_distribution(
    db: AsyncSession = Depends(get_db),
    seniority: Optional[str] = None,
    skill: Optional[str] = None,
):
    """Salary ranges grouped by seniority or filtered by skill."""
    query = (
        select(
            Job.seniority,
            func.count(Job.id).label("count"),
            func.avg(Job.salary_min).label("avg_min"),
            func.avg(Job.salary_max).label("avg_max"),
            func.min(Job.salary_min).label("floor"),
            func.max(Job.salary_max).label("ceiling"),
        )
        .where(Job.is_active == True, Job.salary_min.isnot(None))
    )

    if seniority:
        query = query.where(Job.seniority == seniority)
    if skill:
        query = query.join(JobSkill).join(Skill).where(Skill.name.ilike(f"%{skill}%"))

    query = query.group_by(Job.seniority)

    result = await db.execute(query)
    rows = result.all()

    return {
        "buckets": [
            {
                "seniority": r.seniority or "unknown",
                "count": r.count,
                "avg_min": round(r.avg_min, 0) if r.avg_min else None,
                "avg_max": round(r.avg_max, 0) if r.avg_max else None,
                "floor": r.floor,
                "ceiling": r.ceiling,
            }
            for r in rows
        ],
    }


# ──────────────────────────────────────────────
# Pipeline trigger
# ──────────────────────────────────────────────

@router.post("/pipeline/run")
async def trigger_pipeline(db: AsyncSession = Depends(get_db)):
    """Manually trigger the ingestion pipeline."""
    stats = await run_full_pipeline(db)
    return {"status": "complete", "stats": stats}


# ──────────────────────────────────────────────
# Resume match
# ──────────────────────────────────────────────

# Scoring against every skill we've ever seen would dilute the result — a
# resume shouldn't be penalised for missing a skill that three postings want.
# Scoring against the top slice keeps the number meaningful.
RESUME_DEMAND_POOL = 20
RESUME_DEMAND_WINDOW_DAYS = 30


@router.post("/resume/analyze")
async def analyze_resume(
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
):
    """
    Score an uploaded resume against current skill demand.

    Stateless: the file is parsed in memory and discarded — nothing is written
    to disk or persisted to the database.
    """
    raw = await file.read()
    try:
        text = extract_resume_text(file.filename or "", raw)
    except ResumeParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        await file.close()

    # Same extractor the ingestion pipeline uses, so resume skills and job
    # skills are drawn from one taxonomy and actually comparable.
    resume_skills = {s["name"] for s in extract_skills(text)}

    rows = await _skill_demand_rows(
        db, limit=RESUME_DEMAND_POOL, days=RESUME_DEMAND_WINDOW_DAYS
    )
    in_demand = [r.name for r in rows]

    if not in_demand:
        raise HTTPException(
            status_code=503,
            detail="No skill demand data yet — run the ingestion pipeline first.",
        )

    matched = [name for name in in_demand if name in resume_skills]
    missing = [name for name in in_demand if name not in resume_skills]
    score = round(len(matched) / len(in_demand) * 100)

    return {
        "score": score,
        "matched_skills": matched,
        "missing_skills": missing,
        "resume_skills_found": sorted(resume_skills),
    }
