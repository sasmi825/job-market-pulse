"use client";

import type { Theme } from "@/lib/theme";
import type { Snapshot } from "@/lib/api";
import { formatDateLabel } from "@/lib/format";
import { Card, CardTitle, EmptyNote, ErrorNote, Skeleton } from "./ui";

const W = 720;
const H = 200;
const PAD = 6;

// Grid line fractions, ported from the design.
const GRID_FRACTIONS = [0.25, 0.5, 0.75, 1];

export function TrendChart({
  theme,
  snapshots,
  days,
  loading,
  error,
  onRetry,
}: {
  theme: Theme;
  snapshots: Snapshot[];
  days: number;
  loading: boolean;
  error: string | null;
  onRetry?: () => void;
}) {
  const gridLines = GRID_FRACTIONS.map((f) => H - H * f);

  const values = snapshots.map((s) => s.total_jobs);
  const maxTrend = Math.max(...values, 1);
  const stepX = W / (values.length - 1 || 1);

  const points = values.map((v, i) => [
    i * stepX,
    PAD + (H - PAD * 2) * (1 - v / maxTrend),
  ]);

  const linePath = points
    .map((p, i) => (i === 0 ? "M" : "L") + p[0].toFixed(1) + " " + p[1].toFixed(1))
    .join(" ");
  const areaPath = `${linePath} L${W} ${H} L0 ${H} Z`;

  const firstDate = snapshots[0]?.date ? new Date(snapshots[0].date) : null;
  const lastDate = snapshots.length
    ? new Date(snapshots[snapshots.length - 1].date)
    : null;

  // A single snapshot can't describe a trend — one point renders as a dot with
  // no line, which reads as a broken chart. Say so instead.
  const tooFewPoints = !loading && !error && snapshots.length < 2;

  return (
    <Card theme={theme} style={{ padding: "22px 24px", marginBottom: 24 }}>
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          justifyContent: "space-between",
          marginBottom: 12,
        }}
      >
        <CardTitle>Postings over time</CardTitle>
        <div style={{ fontSize: 12.5, color: theme.textMuted }}>
          Last {days} days
        </div>
      </div>

      {error ? (
        <ErrorNote theme={theme} message={error} onRetry={onRetry} />
      ) : loading ? (
        <Skeleton theme={theme} height={200} style={{ borderRadius: 10 }} />
      ) : (
        <>
          <svg
            viewBox={`0 0 ${W} ${H}`}
            style={{ width: "100%", height: 200, display: "block", overflow: "visible" }}
          >
            {gridLines.map((y, i) => (
              <line
                key={i}
                x1="0"
                x2={W}
                y1={y}
                y2={y}
                stroke={theme.gridLine}
                strokeWidth="1"
              />
            ))}

            {!tooFewPoints && (
              <>
                <path d={areaPath} fill={theme.accentAreaFill} stroke="none" />
                <path
                  d={linePath}
                  fill="none"
                  stroke={theme.accent}
                  strokeWidth="2.5"
                  strokeLinejoin="round"
                  strokeLinecap="round"
                />
              </>
            )}

            {tooFewPoints && snapshots.length === 1 && (
              <circle cx={W / 2} cy={H / 2} r="4" fill={theme.accent} />
            )}
          </svg>

          {tooFewPoints ? (
            <EmptyNote theme={theme} padding={12}>
              {snapshots.length === 1
                ? `Only one daily snapshot so far (${snapshots[0].total_jobs.toLocaleString()} roles). The trend line fills in as the pipeline runs on later days.`
                : "No snapshots in this range yet — run the ingestion pipeline to start the history."}
            </EmptyNote>
          ) : (
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                fontSize: 11.5,
                color: theme.textMuted,
                marginTop: 6,
                fontFamily: "'IBM Plex Mono', monospace",
              }}
            >
              <span>{firstDate ? formatDateLabel(firstDate) : ""}</span>
              <span>{lastDate ? formatDateLabel(lastDate) : ""}</span>
            </div>
          )}
        </>
      )}
    </Card>
  );
}
