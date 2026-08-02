"use client";

import type { Theme } from "@/lib/theme";
import { Card, Skeleton } from "./ui";

export interface Metric {
  label: string;
  value: string;
  caption: string;
}

export function MetricCards({
  theme,
  metrics,
  loading,
  error,
}: {
  theme: Theme;
  metrics: Metric[];
  loading: boolean;
  error: string | null;
}) {
  const placeholders: Metric[] = [
    { label: "Open roles", value: "", caption: "" },
    { label: "Avg salary range", value: "", caption: "" },
    { label: "Companies tracked", value: "", caption: "" },
    { label: "Skills tracked", value: "", caption: "" },
  ];

  const items = loading || error ? placeholders : metrics;

  return (
    <div className="jmp-metrics">
      {items.map((m) => (
        <Card key={m.label} theme={theme} style={{ padding: "20px 22px" }}>
          <div style={{ fontSize: 13, color: theme.textSecondary }}>{m.label}</div>

          {loading ? (
            <Skeleton theme={theme} width="60%" height={28} style={{ marginTop: 8 }} />
          ) : (
            <div
              style={{
                fontSize: 28,
                fontWeight: 600,
                marginTop: 8,
                fontFamily: "'IBM Plex Mono', monospace",
                letterSpacing: "-0.01em",
                // Long values like "$171k–$217k" would otherwise overflow the
                // card on narrow viewports.
                overflowWrap: "anywhere",
              }}
            >
              {error ? "—" : m.value}
            </div>
          )}

          {loading ? (
            <Skeleton theme={theme} width="80%" height={11} style={{ marginTop: 8 }} />
          ) : (
            <div
              style={{ fontSize: 12.5, color: theme.textMuted, marginTop: 6 }}
            >
              {error ? "Unavailable" : m.caption}
            </div>
          )}
        </Card>
      ))}
    </div>
  );
}
