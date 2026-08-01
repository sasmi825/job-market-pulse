/**
 * Typed client for the Job Market Pulse API.
 *
 * All network access lives here — components call these functions rather than
 * reaching for `fetch` themselves.
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export type RangeKey = "7d" | "30d" | "90d";

export const RANGE_DAYS: Record<RangeKey, number> = { "7d": 7, "30d": 30, "90d": 90 };

// ── Response shapes ────────────────────────────────────────────────

export interface Job {
  id: string;
  title: string;
  company: string | null;
  location: string | null;
  location_type: string | null;
  seniority: string | null;
  salary_min: number | null;
  salary_max: number | null;
  source: string;
  posted_at: string | null;
  url: string | null;
  skills: string[];
}

export interface JobsResponse {
  total: number;
  limit: number;
  offset: number;
  jobs: Job[];
}

export interface SkillDemand {
  name: string;
  category: string;
  demand: number;
}

export interface SkillsResponse {
  /** Distinct skills in the window — not capped by `limit`, unlike `skills`. */
  total: number;
  period_days: number;
  skills: SkillDemand[];
}

export interface CompanyHiring {
  name: string;
  open_roles: number;
}

export interface CompaniesResponse {
  companies: CompanyHiring[];
}

export interface Snapshot {
  date: string;
  total_jobs: number;
  new_jobs: number;
  avg_salary_min: number | null;
  avg_salary_max: number | null;
  top_skills: Record<string, number> | null;
}

export interface TrendsResponse {
  period_days: number;
  snapshots: Snapshot[];
}

export interface SalaryBucket {
  seniority: string;
  count: number;
  avg_min: number | null;
  avg_max: number | null;
  floor: number | null;
  ceiling: number | null;
}

export interface SalariesResponse {
  buckets: SalaryBucket[];
}

export interface ResumeAnalysis {
  score: number;
  matched_skills: string[];
  missing_skills: string[];
  resume_skills_found: string[];
}

export interface JobFilters {
  locationType?: string;
  seniority?: string;
  search?: string;
  limit?: number;
  offset?: number;
}

// ── Core fetch helper ──────────────────────────────────────────────

/** Thrown for any non-2xx response, carrying the API's `detail` when present. */
export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, { ...init, cache: "no-store" });
  } catch {
    // fetch only rejects on network-level failure — the API being down reads
    // as a TypeError here, which is useless to show a user.
    throw new ApiError("Can't reach the API. Is the backend running?", 0);
  }

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      /* response wasn't JSON; keep the status-code message */
    }
    throw new ApiError(detail, res.status);
  }

  return (await res.json()) as T;
}

function qs(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "" && value !== "all") {
      search.set(key, String(value));
    }
  }
  const s = search.toString();
  return s ? `?${s}` : "";
}

// ── Endpoints ──────────────────────────────────────────────────────

export function getJobs(filters: JobFilters = {}): Promise<JobsResponse> {
  return request<JobsResponse>(
    `/jobs${qs({
      location_type: filters.locationType,
      seniority: filters.seniority,
      search: filters.search,
      limit: filters.limit ?? 50,
      offset: filters.offset,
    })}`,
  );
}

export function getTopSkills(days: number, limit = 10): Promise<SkillsResponse> {
  return request<SkillsResponse>(`/skills/top${qs({ days, limit })}`);
}

export function getCompaniesHiring(limit = 10): Promise<CompaniesResponse> {
  return request<CompaniesResponse>(`/companies/hiring${qs({ limit })}`);
}

export function getTrends(days: number): Promise<TrendsResponse> {
  return request<TrendsResponse>(`/trends${qs({ days })}`);
}

export function getSalaries(): Promise<SalariesResponse> {
  return request<SalariesResponse>("/salaries");
}

export function analyzeResume(file: File): Promise<ResumeAnalysis> {
  const body = new FormData();
  body.append("file", file);
  return request<ResumeAnalysis>("/resume/analyze", { method: "POST", body });
}
