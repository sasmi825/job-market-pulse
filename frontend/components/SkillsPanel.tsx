"use client";

import type { Theme } from "@/lib/theme";
import type { SkillDemand } from "@/lib/api";
import { Card, CardTitle, EmptyNote, ErrorNote, Skeleton } from "./ui";

export function SkillsPanel({
  theme,
  skills,
  loading,
  error,
  onRetry,
}: {
  theme: Theme;
  skills: SkillDemand[];
  loading: boolean;
  error: string | null;
  onRetry?: () => void;
}) {
  const max = skills.length ? skills[0].demand : 1;

  return (
    <Card theme={theme} style={{ padding: "22px 24px" }}>
      <div style={{ marginBottom: 14 }}>
        <CardTitle>Top skills in demand</CardTitle>
      </div>

      {error ? (
        <ErrorNote theme={theme} message={error} onRetry={onRetry} />
      ) : loading ? (
        <div>
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} style={{ marginBottom: 11 }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  marginBottom: 4,
                }}
              >
                <Skeleton theme={theme} width={90} height={13} />
                <Skeleton theme={theme} width={28} height={13} />
              </div>
              <Skeleton theme={theme} height={7} style={{ borderRadius: 4 }} />
            </div>
          ))}
        </div>
      ) : skills.length === 0 ? (
        <EmptyNote theme={theme}>No skills extracted in this range yet.</EmptyNote>
      ) : (
        skills.map((s) => (
          <div key={s.name} style={{ marginBottom: 11 }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                fontSize: 13,
                marginBottom: 4,
                gap: 12,
              }}
            >
              {/* Real skill names can be long (e.g. "GitHub Actions"); keep the
                  count pinned right rather than letting it wrap. */}
              <span
                style={{
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {s.name}
              </span>
              <span
                style={{
                  fontFamily: "'IBM Plex Mono', monospace",
                  color: theme.textSecondary,
                  flexShrink: 0,
                }}
              >
                {s.demand}
              </span>
            </div>
            <div
              style={{
                height: 7,
                background: theme.subtleBg,
                borderRadius: 4,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  height: "100%",
                  width: `${Math.round((s.demand / max) * 100)}%`,
                  background: theme.accent,
                  borderRadius: 4,
                }}
              />
            </div>
          </div>
        ))
      )}
    </Card>
  );
}
