"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  ApiError,
  RANGE_DAYS,
  getCompaniesHiring,
  getJobs,
  getSalaries,
  getTopSkills,
  getTrends,
  type CompanyHiring,
  type Job,
  type RangeKey,
  type SalaryBucket,
  type SkillDemand,
  type Snapshot,
} from "@/lib/api";
import { THEMES, type ThemeName } from "@/lib/theme";
import { fmtK, formatUpdatedAt } from "@/lib/format";
import { useDebounced } from "@/lib/useDebounced";

import { Header } from "@/components/Header";
import { Hero } from "@/components/Hero";
import { MetricCards, type Metric } from "@/components/MetricCards";
import { ResumeMatch } from "@/components/ResumeMatch";
import { TrendChart } from "@/components/TrendChart";
import { SkillsPanel } from "@/components/SkillsPanel";
import { CompaniesPanel } from "@/components/CompaniesPanel";
import { SalaryBands } from "@/components/SalaryBands";
import { JobsTable, type Filters } from "@/components/JobsTable";

const JOBS_PAGE_SIZE = 50;
// Counts for the "tracked" metrics; the API caps both at 50.
const METRIC_POOL_LIMIT = 50;

function errorMessage(err: unknown): string {
  return err instanceof ApiError ? err.message : "Something went wrong.";
}

export default function Page() {
  const [themeName, setThemeName] = useState<ThemeName>("light");
  const [range, setRange] = useState<RangeKey>("30d");
  const [filters, setFilters] = useState<Filters>({
    locationType: "all",
    seniority: "all",
    query: "",
  });

  const theme = THEMES[themeName];
  const days = RANGE_DAYS[range];

  // Search fires on a delay so typing doesn't hit the API per keystroke.
  const debouncedQuery = useDebounced(filters.query, 350);

  // ── Range-scoped data (skills + trends) ──────────────────────────
  const [skills, setSkills] = useState<SkillDemand[]>([]);
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [rangeLoading, setRangeLoading] = useState(true);
  const [skillsError, setSkillsError] = useState<string | null>(null);
  const [trendsError, setTrendsError] = useState<string | null>(null);

  // ── Range-independent data ───────────────────────────────────────
  const [companies, setCompanies] = useState<CompanyHiring[]>([]);
  const [salaries, setSalaries] = useState<SalaryBucket[]>([]);
  const [skillPoolCount, setSkillPoolCount] = useState<number | null>(null);
  const [companyPoolCount, setCompanyPoolCount] = useState<number | null>(null);
  const [companyNames, setCompanyNames] = useState<string[]>([]);
  const [grandTotal, setGrandTotal] = useState<number | null>(null);
  const [overviewLoading, setOverviewLoading] = useState(true);
  const [overviewError, setOverviewError] = useState<string | null>(null);

  // ── Jobs table ───────────────────────────────────────────────────
  const [jobs, setJobs] = useState<Job[]>([]);
  const [jobsTotal, setJobsTotal] = useState(0);
  const [jobsLoading, setJobsLoading] = useState(true);
  const [jobsError, setJobsError] = useState<string | null>(null);

  const [updatedAt, setUpdatedAt] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const reload = useCallback(() => setReloadKey((k) => k + 1), []);

  // Rendered on the client only — formatting it during SSR would produce the
  // server's locale/timezone and trip a hydration mismatch.
  useEffect(() => {
    setUpdatedAt(formatUpdatedAt(new Date()));
  }, [reloadKey]);

  useEffect(() => {
    let cancelled = false;
    setRangeLoading(true);
    setSkillsError(null);
    setTrendsError(null);

    Promise.allSettled([getTopSkills(days, 10), getTrends(days)]).then(
      ([skillsRes, trendsRes]) => {
        if (cancelled) return;

        if (skillsRes.status === "fulfilled") setSkills(skillsRes.value.skills);
        else setSkillsError(errorMessage(skillsRes.reason));

        if (trendsRes.status === "fulfilled") setSnapshots(trendsRes.value.snapshots);
        else setTrendsError(errorMessage(trendsRes.reason));

        setRangeLoading(false);
      },
    );

    return () => {
      cancelled = true;
    };
  }, [days, reloadKey]);

  useEffect(() => {
    let cancelled = false;
    setOverviewLoading(true);
    setOverviewError(null);

    Promise.all([
      getCompaniesHiring(METRIC_POOL_LIMIT),
      getSalaries(),
      getTopSkills(90, METRIC_POOL_LIMIT),
      getJobs({ limit: 1 }),
    ])
      .then(([companiesRes, salariesRes, skillPool, jobsHead]) => {
        if (cancelled) return;
        setCompanies(companiesRes.companies.slice(0, 10));
        setCompanyPoolCount(companiesRes.companies.length);
        setCompanyNames(companiesRes.companies.slice(0, 3).map((c) => c.name));
        setSalaries(salariesRes.buckets);
        setSkillPoolCount(skillPool.total);
        setGrandTotal(jobsHead.total);
        setOverviewLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        setOverviewError(errorMessage(err));
        setOverviewLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  useEffect(() => {
    let cancelled = false;
    setJobsLoading(true);
    setJobsError(null);

    getJobs({
      locationType: filters.locationType,
      seniority: filters.seniority,
      search: debouncedQuery.trim() || undefined,
      limit: JOBS_PAGE_SIZE,
    })
      .then((res) => {
        if (cancelled) return;
        setJobs(res.jobs);
        setJobsTotal(res.total);
        setJobsLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        setJobsError(errorMessage(err));
        setJobsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [filters.locationType, filters.seniority, debouncedQuery, reloadKey]);

  const metrics: Metric[] = useMemo(() => {
    // Weight each bucket by its role count so the headline range reflects the
    // dataset rather than treating a 2-role bucket like a 244-role one.
    const withSalary = salaries.filter((b) => b.avg_min != null && b.avg_max != null);
    const roleCount = withSalary.reduce((sum, b) => sum + b.count, 0);
    const avgMin = roleCount
      ? withSalary.reduce((sum, b) => sum + (b.avg_min as number) * b.count, 0) / roleCount
      : null;
    const avgMax = roleCount
      ? withSalary.reduce((sum, b) => sum + (b.avg_max as number) * b.count, 0) / roleCount
      : null;

    return [
      {
        label: "Open roles",
        value: grandTotal != null ? grandTotal.toLocaleString() : "—",
        caption:
          companyPoolCount != null ? `Across ${companyPoolCount} companies` : "—",
      },
      {
        label: "Avg salary range",
        value: avgMin != null && avgMax != null ? `${fmtK(avgMin)}–${fmtK(avgMax)}` : "—",
        caption: roleCount ? `From ${roleCount.toLocaleString()} posted ranges` : "No ranges posted",
      },
      {
        label: "Companies tracked",
        value: companyPoolCount != null ? String(companyPoolCount) : "—",
        caption: "Career pages scraped daily",
      },
      {
        label: "Skills tracked",
        value: skillPoolCount != null ? String(skillPoolCount) : "—",
        caption: "Parsed from job descriptions",
      },
    ];
  }, [salaries, grandTotal, companyPoolCount, skillPoolCount]);

  return (
    <div
      className="jmp-page"
      style={{
        minHeight: "100vh",
        boxSizing: "border-box",
        color: theme.text,
        background: theme.pageBg,
        transition: "background 0.2s ease, color 0.2s ease",
        maxWidth: 1400,
        margin: "0 auto",
      }}
    >
      <Header theme={theme} themeName={themeName} onThemeChange={setThemeName} />

      <Hero
        theme={theme}
        range={range}
        onRangeChange={setRange}
        companyCount={companyPoolCount}
        companyNames={companyNames}
        updatedAt={updatedAt}
      />

      <MetricCards
        theme={theme}
        metrics={metrics}
        loading={overviewLoading}
        error={overviewError}
      />

      <ResumeMatch theme={theme} />

      <TrendChart
        theme={theme}
        snapshots={snapshots}
        days={days}
        loading={rangeLoading}
        error={trendsError}
        onRetry={reload}
      />

      <div className="jmp-two-col">
        <SkillsPanel
          theme={theme}
          skills={skills}
          loading={rangeLoading}
          error={skillsError}
          onRetry={reload}
        />
        <CompaniesPanel
          theme={theme}
          companies={companies}
          loading={overviewLoading}
          error={overviewError}
          onRetry={reload}
        />
      </div>

      <SalaryBands
        theme={theme}
        buckets={salaries}
        loading={overviewLoading}
        error={overviewError}
        onRetry={reload}
      />

      <JobsTable
        theme={theme}
        jobs={jobs}
        total={jobsTotal}
        grandTotal={grandTotal}
        filters={filters}
        onFiltersChange={setFilters}
        loading={jobsLoading}
        error={jobsError}
        onRetry={reload}
      />
    </div>
  );
}
