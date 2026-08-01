"use client";

import type { Theme } from "@/lib/theme";
import type { Job } from "@/lib/api";
import { fmtRange, postedLabel, skillsLabel, titleCase } from "@/lib/format";
import { Card, CardTitle, ErrorNote, Skeleton } from "./ui";

// API values are lowercase; labels follow the design's capitalisation.
const LOCATION_OPTIONS = [
  { value: "all", label: "All locations" },
  { value: "remote", label: "Remote" },
  { value: "hybrid", label: "Hybrid" },
  { value: "onsite", label: "Onsite" },
];

const SENIORITY_OPTIONS = [
  { value: "all", label: "All levels" },
  { value: "intern", label: "Intern" },
  { value: "junior", label: "Junior" },
  { value: "mid", label: "Mid" },
  { value: "senior", label: "Senior" },
  { value: "lead", label: "Lead" },
  { value: "staff", label: "Staff" },
];

const COLUMNS = ["Title", "Company", "Location", "Seniority", "Salary", "Skills", "Posted"];

export interface Filters {
  locationType: string;
  seniority: string;
  query: string;
}

export function JobsTable({
  theme,
  jobs,
  total,
  grandTotal,
  filters,
  onFiltersChange,
  loading,
  error,
  onRetry,
}: {
  theme: Theme;
  jobs: Job[];
  total: number;
  grandTotal: number | null;
  filters: Filters;
  onFiltersChange: (f: Filters) => void;
  loading: boolean;
  error: string | null;
  onRetry?: () => void;
}) {
  const dotColor = (locationType: string | null) => {
    switch ((locationType ?? "").toLowerCase()) {
      case "remote":
        return theme.accentSecondary;
      case "hybrid":
        return theme.accent;
      default:
        return theme.neutralDot;
    }
  };

  const selectStyle: React.CSSProperties = {
    border: `1px solid ${theme.borderStrong}`,
    background: theme.inputBg,
    borderRadius: 7,
    padding: "7px 10px",
    fontSize: 12.5,
    fontFamily: "inherit",
    color: theme.textStrong,
  };

  const thStyle: React.CSSProperties = {
    textAlign: "left",
    padding: "10px 8px",
    fontWeight: 500,
    color: theme.textSecondary,
    fontSize: 12,
    borderBottom: `1px solid ${theme.border}`,
  };

  return (
    <Card theme={theme} style={{ padding: "22px 24px" }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 12,
          marginBottom: 16,
        }}
      >
        <CardTitle>Open roles</CardTitle>

        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
          <select
            value={filters.locationType}
            onChange={(e) =>
              onFiltersChange({ ...filters, locationType: e.target.value })
            }
            aria-label="Filter by location type"
            style={selectStyle}
          >
            {LOCATION_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>

          <select
            value={filters.seniority}
            onChange={(e) =>
              onFiltersChange({ ...filters, seniority: e.target.value })
            }
            aria-label="Filter by seniority"
            style={selectStyle}
          >
            {SENIORITY_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>

          <input
            value={filters.query}
            onChange={(e) => onFiltersChange({ ...filters, query: e.target.value })}
            placeholder="Search skill or title"
            aria-label="Search by skill or title"
            style={{ ...selectStyle, width: 190 }}
          />

          <span
            style={{
              fontSize: 12.5,
              color: theme.textMuted,
              fontFamily: "'IBM Plex Mono', monospace",
              whiteSpace: "nowrap",
            }}
          >
            {/* `total` is the match count, but only the first page is on
                screen — say so rather than implying all 1,122 are rendered. */}
            {loading
              ? "…"
              : jobs.length < total
                ? `Showing ${jobs.length} of ${total.toLocaleString()} roles`
                : grandTotal != null && total < grandTotal
                  ? `${total.toLocaleString()} of ${grandTotal.toLocaleString()} roles`
                  : `${total.toLocaleString()} roles`}
          </span>
        </div>
      </div>

      {error ? (
        <ErrorNote theme={theme} message={error} onRetry={onRetry} />
      ) : (
        <div
          style={{
            maxHeight: 560,
            overflow: "auto",
            borderTop: `1px solid ${theme.border}`,
          }}
        >
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ position: "sticky", top: 0, background: theme.card, zIndex: 1 }}>
                {COLUMNS.map((c) => (
                  <th
                    key={c}
                    style={{
                      ...thStyle,
                      textAlign: c === "Posted" ? "right" : "left",
                    }}
                  >
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading
                ? Array.from({ length: 12 }).map((_, i) => (
                    <tr key={i} style={{ borderBottom: `1px solid ${theme.rowBorder}` }}>
                      {COLUMNS.map((c) => (
                        <td key={c} style={{ padding: "10px 8px" }}>
                          <Skeleton theme={theme} height={12} />
                        </td>
                      ))}
                    </tr>
                  ))
                : jobs.map((job) => (
                    <tr key={job.id} style={{ borderBottom: `1px solid ${theme.rowBorder}` }}>
                      <td style={{ padding: "10px 8px", fontWeight: 500 }}>
                        {job.url ? (
                          <a
                            href={job.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{ color: "inherit" }}
                          >
                            {job.title}
                          </a>
                        ) : (
                          job.title
                        )}
                      </td>
                      <td style={{ padding: "10px 8px", color: theme.textStrong }}>
                        {job.company ?? "—"}
                      </td>
                      <td style={{ padding: "10px 8px", color: theme.textSecondary }}>
                        <span
                          style={{
                            display: "inline-block",
                            width: 6,
                            height: 6,
                            borderRadius: "50%",
                            background: dotColor(job.location_type),
                            marginRight: 6,
                            flexShrink: 0,
                          }}
                        />
                        {job.location || "—"}
                      </td>
                      <td style={{ padding: "10px 8px" }}>
                        <span
                          style={{
                            background: theme.subtleBg,
                            borderRadius: 5,
                            padding: "3px 8px",
                            fontSize: 11.5,
                            color: theme.textStrong,
                            whiteSpace: "nowrap",
                          }}
                        >
                          {titleCase(job.seniority)}
                        </span>
                      </td>
                      <td
                        style={{
                          padding: "10px 8px",
                          fontFamily: "'IBM Plex Mono', monospace",
                          color: job.salary_min == null ? theme.textMuted : theme.textStrong,
                          whiteSpace: "nowrap",
                        }}
                      >
                        {fmtRange(job.salary_min, job.salary_max)}
                      </td>
                      <td
                        style={{
                          padding: "10px 8px",
                          color: theme.textSecondary,
                          fontSize: 12,
                        }}
                        title={job.skills.join(", ")}
                      >
                        {skillsLabel(job.skills)}
                      </td>
                      <td
                        style={{
                          padding: "10px 8px",
                          textAlign: "right",
                          color: theme.textMuted,
                          fontSize: 12,
                          whiteSpace: "nowrap",
                        }}
                      >
                        {postedLabel(job.posted_at)}
                      </td>
                    </tr>
                  ))}
            </tbody>
          </table>

          {!loading && jobs.length === 0 && (
            <div
              style={{
                padding: 40,
                textAlign: "center",
                color: theme.textMuted,
                fontSize: 13,
              }}
            >
              No roles match these filters.
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
