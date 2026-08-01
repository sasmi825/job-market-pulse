"use client";

import type { Theme } from "@/lib/theme";
import type { SalaryBucket } from "@/lib/api";
import { fmtK, titleCase } from "@/lib/format";
import { Card, CardTitle, EmptyNote, ErrorNote, Skeleton } from "./ui";

// The API returns buckets in whatever order the GROUP BY produced; the design
// reads as a ladder, so impose a sensible progression.
const SENIORITY_ORDER = ["intern", "junior", "mid", "senior", "lead", "staff"];

function rank(seniority: string): number {
  const i = SENIORITY_ORDER.indexOf(seniority.toLowerCase());
  return i === -1 ? SENIORITY_ORDER.length : i;
}

export function SalaryBands({
  theme,
  buckets,
  loading,
  error,
  onRetry,
}: {
  theme: Theme;
  buckets: SalaryBucket[];
  loading: boolean;
  error: string | null;
  onRetry?: () => void;
}) {
  const usable = buckets
    .filter((b) => b.avg_min != null && b.avg_max != null)
    .sort((a, b) => rank(a.seniority) - rank(b.seniority));

  // Scale to the average band, not floor/ceiling. A handful of postings quote
  // non-USD figures with a bare "$" (a Taiwan role parses as $2.4M), and
  // scaling to those outliers would squash every real band into a sliver.
  const mins = usable.map((b) => b.avg_min as number);
  const maxes = usable.map((b) => b.avg_max as number);
  const globalMin = mins.length ? Math.min(...mins) : 0;
  const globalMax = maxes.length ? Math.max(...maxes) : 1;
  const span = globalMax - globalMin || 1;

  return (
    <Card theme={theme} style={{ padding: "22px 24px", marginBottom: 24 }}>
      <div style={{ marginBottom: 16 }}>
        <CardTitle>Salary by seniority</CardTitle>
      </div>

      {error ? (
        <ErrorNote theme={theme} message={error} onRetry={onRetry} />
      ) : loading ? (
        <div>
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              style={{
                display: "grid",
                gridTemplateColumns: "90px 1fr 150px",
                alignItems: "center",
                gap: 14,
                padding: "9px 0",
              }}
            >
              <Skeleton theme={theme} width={60} height={13} />
              <Skeleton theme={theme} height={10} style={{ borderRadius: 5 }} />
              <Skeleton theme={theme} width={110} height={12} style={{ justifySelf: "end" }} />
            </div>
          ))}
        </div>
      ) : usable.length === 0 ? (
        <EmptyNote theme={theme}>
          No salary data available yet — most postings don&apos;t publish a range.
        </EmptyNote>
      ) : (
        usable.map((b) => {
          const min = b.avg_min as number;
          const max = b.avg_max as number;
          const avg = (min + max) / 2;
          return (
            <div
              key={b.seniority}
              style={{
                display: "grid",
                gridTemplateColumns: "90px 1fr 150px",
                alignItems: "center",
                gap: 14,
                padding: "9px 0",
              }}
            >
              <span style={{ fontSize: 13, fontWeight: 500 }}>
                {titleCase(b.seniority)}
              </span>
              <div
                style={{
                  position: "relative",
                  height: 10,
                  background: theme.subtleBg,
                  borderRadius: 5,
                }}
              >
                <div
                  style={{
                    position: "absolute",
                    top: 0,
                    bottom: 0,
                    left: `${((min - globalMin) / span) * 100}%`,
                    width: `${((max - min) / span) * 100}%`,
                    background: theme.accentBandFill,
                    borderRadius: 5,
                  }}
                />
                <div
                  style={{
                    position: "absolute",
                    top: -3,
                    left: `${((avg - globalMin) / span) * 100}%`,
                    width: 2,
                    height: 16,
                    background: theme.accentStrong,
                    borderRadius: 1,
                  }}
                />
              </div>
              <span
                style={{
                  fontSize: 12.5,
                  fontFamily: "'IBM Plex Mono', monospace",
                  color: theme.textSecondary,
                  textAlign: "right",
                  whiteSpace: "nowrap",
                }}
                title={`${b.count} roles with a published range`}
              >
                {fmtK(min)}–{fmtK(max)}
              </span>
            </div>
          );
        })
      )}
    </Card>
  );
}
