"use client";

import type { Theme } from "@/lib/theme";
import { cardStyle } from "@/lib/theme";

/** Card shell shared by every panel — rounded, subtle border, soft shadow. */
export function Card({
  theme,
  children,
  style,
}: {
  theme: Theme;
  children: React.ReactNode;
  style?: React.CSSProperties;
}) {
  return <div style={{ ...cardStyle(theme), ...style }}>{children}</div>;
}

export function CardTitle({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ fontSize: 14.5, fontWeight: 600 }}>{children}</div>
  );
}

/**
 * Skeleton placeholder. The prototype had no loading states because its data
 * was generated synchronously; these hold the same footprint as the real
 * content so nothing jumps when a fetch resolves.
 */
export function Skeleton({
  theme,
  width = "100%",
  height = 12,
  style,
}: {
  theme: Theme;
  width?: number | string;
  height?: number | string;
  style?: React.CSSProperties;
}) {
  return (
    <div
      className="jmp-skeleton"
      style={{ background: theme.subtleBg, width, height, ...style }}
    />
  );
}

/** Inline error, styled to sit inside a card without breaking its rhythm. */
export function ErrorNote({
  theme,
  message,
  onRetry,
}: {
  theme: Theme;
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div
      style={{
        fontSize: 13,
        color: theme.textSecondary,
        padding: "20px 0",
        display: "flex",
        alignItems: "center",
        gap: 10,
        flexWrap: "wrap",
      }}
    >
      <span>{message}</span>
      {onRetry && (
        <button
          onClick={onRetry}
          style={{
            border: `1px solid ${theme.borderStrong}`,
            background: theme.inputBg,
            color: theme.textStrong,
            fontSize: 12.5,
            fontWeight: 500,
            padding: "5px 10px",
            borderRadius: 7,
            cursor: "pointer",
            fontFamily: "inherit",
          }}
        >
          Retry
        </button>
      )}
    </div>
  );
}

/** Centred note used where a panel has no data to draw. */
export function EmptyNote({
  theme,
  children,
  padding = 40,
}: {
  theme: Theme;
  children: React.ReactNode;
  padding?: number;
}) {
  return (
    <div
      style={{
        padding,
        textAlign: "center",
        color: theme.textMuted,
        fontSize: 13,
      }}
    >
      {children}
    </div>
  );
}
