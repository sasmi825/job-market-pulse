"use client";

import type { Theme } from "@/lib/theme";
import type { CompanyHiring } from "@/lib/api";
import { Card, CardTitle, EmptyNote, ErrorNote, Skeleton } from "./ui";

export function CompaniesPanel({
  theme,
  companies,
  loading,
  error,
  onRetry,
}: {
  theme: Theme;
  companies: CompanyHiring[];
  loading: boolean;
  error: string | null;
  onRetry?: () => void;
}) {
  const max = companies.length ? companies[0].open_roles : 1;

  return (
    <Card theme={theme} style={{ padding: "22px 24px" }}>
      <div style={{ marginBottom: 14 }}>
        <CardTitle>Companies by open roles</CardTitle>
      </div>

      {error ? (
        <ErrorNote theme={theme} message={error} onRetry={onRetry} />
      ) : loading ? (
        <div>
          {Array.from({ length: 8 }).map((_, i) => (
            <div
              key={i}
              style={{ display: "flex", alignItems: "center", gap: 12, padding: "7px 0" }}
            >
              <Skeleton theme={theme} width={16} height={12} />
              <div style={{ flex: 1 }}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    marginBottom: 4,
                  }}
                >
                  <Skeleton theme={theme} width={100} height={13} />
                  <Skeleton theme={theme} width={24} height={13} />
                </div>
                <Skeleton theme={theme} height={5} style={{ borderRadius: 3 }} />
              </div>
            </div>
          ))}
        </div>
      ) : companies.length === 0 ? (
        <EmptyNote theme={theme}>No companies with open roles yet.</EmptyNote>
      ) : (
        companies.map((c, idx) => (
          <div
            key={c.name}
            style={{ display: "flex", alignItems: "center", gap: 12, padding: "7px 0" }}
          >
            <span
              style={{
                fontFamily: "'IBM Plex Mono', monospace",
                fontSize: 12,
                color: theme.textMuted,
                width: 16,
                flexShrink: 0,
              }}
            >
              {idx + 1}
            </span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: 13,
                  marginBottom: 4,
                  gap: 12,
                }}
              >
                {/* Real names run long ("Recruiting Systems and Data"), so clip
                    rather than let the row wrap and break the bar alignment. */}
                <span
                  style={{
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                  title={c.name}
                >
                  {c.name}
                </span>
                <span
                  style={{
                    fontFamily: "'IBM Plex Mono', monospace",
                    color: theme.textSecondary,
                    flexShrink: 0,
                  }}
                >
                  {c.open_roles}
                </span>
              </div>
              <div
                style={{
                  height: 5,
                  background: theme.subtleBg,
                  borderRadius: 3,
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    height: "100%",
                    width: `${Math.round((c.open_roles / max) * 100)}%`,
                    background: theme.accentSecondary,
                    borderRadius: 3,
                  }}
                />
              </div>
            </div>
          </div>
        ))
      )}
    </Card>
  );
}
