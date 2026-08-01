"use client";

import type { Theme } from "@/lib/theme";
import type { RangeKey } from "@/lib/api";

const RANGES: RangeKey[] = ["7d", "30d", "90d"];

export function Hero({
  theme,
  range,
  onRangeChange,
  companyCount,
  companyNames,
  updatedAt,
}: {
  theme: Theme;
  range: RangeKey;
  onRangeChange: (r: RangeKey) => void;
  companyCount: number | null;
  companyNames: string[];
  updatedAt: string | null;
}) {
  // The prototype named Stripe/Airbnb/Netflix and "22 others" as static copy.
  // Only companies actually in the dataset should be named, so this is built
  // from the live leaderboard instead.
  const named = companyNames.join(", ");
  const others =
    companyCount != null ? Math.max(companyCount - companyNames.length, 0) : null;

  return (
    <div style={{ padding: "56px 4px 40px" }}>
      <h1
        style={{
          margin: 0,
          fontSize: 44,
          fontWeight: 600,
          letterSpacing: "-0.02em",
          lineHeight: 1.1,
          maxWidth: 640,
        }}
      >
        The job market, tracked daily.
      </h1>
      <p
        style={{
          margin: "16px 0 0",
          fontSize: 16,
          color: theme.textSecondary,
          maxWidth: 560,
          lineHeight: 1.55,
        }}
      >
        Real postings pulled straight from company career pages
        {named && (
          <>
            {" "}
            — {named}
            {others ? ` and ${others} others` : ""}
          </>
        )}{" "}
        — so you can see what&apos;s actually being hired for right now.
      </p>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 16,
          marginTop: 32,
          flexWrap: "wrap",
        }}
      >
        <span
          style={{
            fontSize: 12.5,
            color: theme.textMuted,
            fontFamily: "'IBM Plex Mono', monospace",
          }}
        >
          {updatedAt ? `Updated ${updatedAt}` : "Updated —"}
        </span>

        <div
          style={{
            display: "flex",
            background: theme.subtleBg,
            padding: 3,
            borderRadius: 8,
            gap: 2,
          }}
        >
          {RANGES.map((r) => {
            const active = range === r;
            return (
              <button
                key={r}
                onClick={() => onRangeChange(r)}
                aria-pressed={active}
                style={{
                  border: "none",
                  background: active ? theme.card : "transparent",
                  color: active ? theme.text : theme.textMuted,
                  fontSize: 12.5,
                  fontWeight: 500,
                  padding: "6px 12px",
                  borderRadius: 6,
                  cursor: "pointer",
                  fontFamily: "inherit",
                  boxShadow: active ? "0 1px 2px oklch(0 0 0 / 0.06)" : "none",
                }}
              >
                {r}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
