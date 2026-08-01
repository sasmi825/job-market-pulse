"""Shared types for scrapers."""

from dataclasses import dataclass, field


@dataclass
class ScrapeResult:
    """
    Outcome of scraping one source.

    Scrapers swallow per-company errors so one dead board can't abort a run,
    but that made a fully broken source indistinguishable from a quiet one —
    every Lever slug 404'd for weeks while the pipeline reported success.
    Carrying the failures back lets the caller report them.
    """

    source: str
    jobs: list[dict] = field(default_factory=list)
    # Slugs that errored outright (404, network failure, bad payload).
    failed_companies: list[str] = field(default_factory=list)
    # Slugs that responded fine but currently list nothing — not a failure.
    empty_companies: list[str] = field(default_factory=list)
    attempted: int = 0

    @property
    def is_broken(self) -> bool:
        """True when the source produced nothing and at least one call failed."""
        return not self.jobs and bool(self.failed_companies)

    def summary(self) -> dict:
        return {
            "jobs": len(self.jobs),
            "companies_attempted": self.attempted,
            "companies_failed": sorted(self.failed_companies),
            "companies_empty": sorted(self.empty_companies),
        }
