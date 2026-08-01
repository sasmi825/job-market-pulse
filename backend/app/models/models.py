import uuid
from datetime import datetime, date

from sqlalchemy import (
    String, Text, Integer, Float, DateTime, Date,
    ForeignKey, UniqueConstraint, Index, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    industry: Mapped[str | None] = mapped_column(String(255))
    size_bucket: Mapped[str | None] = mapped_column(String(50))  # startup, mid, enterprise
    careers_url: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    jobs: Mapped[list["Job"]] = relationship(back_populates="company")


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(50))  # language, framework, tool, cloud, soft_skill

    jobs: Mapped[list["JobSkill"]] = relationship(back_populates="skill")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id: Mapped[str] = mapped_column(String(255), index=True)
    source: Mapped[str] = mapped_column(String(50))  # greenhouse, lever, adzuna
    title: Mapped[str] = mapped_column(String(500))
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    location: Mapped[str | None] = mapped_column(String(255))
    location_type: Mapped[str | None] = mapped_column(String(50))  # remote, hybrid, onsite
    salary_min: Mapped[float | None] = mapped_column(Float)
    salary_max: Mapped[float | None] = mapped_column(Float)
    salary_currency: Mapped[str | None] = mapped_column(String(10), default="USD")
    description: Mapped[str | None] = mapped_column(Text)
    seniority: Mapped[str | None] = mapped_column(String(50))  # junior, mid, senior, lead, staff
    posted_at: Mapped[datetime | None] = mapped_column(DateTime)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(default=True)

    company: Mapped["Company"] = relationship(back_populates="jobs")
    skills: Mapped[list["JobSkill"]] = relationship(back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("external_id", "source", name="uq_job_source"),
        Index("ix_jobs_posted_at", "posted_at"),
    )


class JobSkill(Base):
    __tablename__ = "job_skills"

    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True)
    skill_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("skills.id"), primary_key=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)  # how sure we are about extraction

    job: Mapped["Job"] = relationship(back_populates="skills")
    skill: Mapped["Skill"] = relationship(back_populates="jobs")


class DailySnapshot(Base):
    __tablename__ = "daily_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    snapshot_date: Mapped[date] = mapped_column(Date, unique=True, index=True)
    total_jobs: Mapped[int] = mapped_column(Integer, default=0)
    new_jobs: Mapped[int] = mapped_column(Integer, default=0)
    avg_salary_min: Mapped[float | None] = mapped_column(Float)
    avg_salary_max: Mapped[float | None] = mapped_column(Float)
    top_skills: Mapped[dict | None] = mapped_column(JSON)  # {"React": 45, "Python": 38, ...}
    top_companies: Mapped[dict | None] = mapped_column(JSON)  # {"Google": 12, "Meta": 8, ...}
    top_locations: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
