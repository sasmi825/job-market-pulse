"use client";

import type { Theme, ThemeName } from "@/lib/theme";

export function Header({
  theme,
  themeName,
  onThemeChange,
}: {
  theme: Theme;
  themeName: ThemeName;
  onThemeChange: (t: ThemeName) => void;
}) {
  const isDark = themeName === "dark";
  const activeShadow = "0 1px 2px oklch(0 0 0 / 0.06)";

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 16,
        position: "sticky",
        top: 0,
        zIndex: 5,
        padding: "14px 20px",
        margin: "0 -20px 0",
        background: theme.headerBg,
        backdropFilter: "blur(16px)",
        WebkitBackdropFilter: "blur(16px)",
        borderRadius: 16,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <span
          style={{
            width: 28,
            height: 28,
            borderRadius: 8,
            background: theme.accent,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
          }}
        >
          <svg
            width="17"
            height="17"
            viewBox="0 0 24 24"
            fill="none"
            stroke="oklch(0.99 0 0)"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M2 12h4l2.5-7 4 14 2.5-7H22" />
          </svg>
        </span>
        <span style={{ fontSize: 14.5, fontWeight: 600, letterSpacing: "-0.01em" }}>
          Job Market Pulse
        </span>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <button
          onClick={() => onThemeChange("light")}
          aria-label="Light theme"
          aria-pressed={!isDark}
          style={{
            border: "none",
            background: !isDark ? theme.card : "transparent",
            boxShadow: !isDark ? activeShadow : "none",
            width: 30,
            height: 30,
            borderRadius: 8,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <svg
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="none"
            stroke={!isDark ? theme.text : theme.textMuted}
            strokeWidth="2"
            strokeLinecap="round"
          >
            <circle cx="12" cy="12" r="4.5" />
            <line x1="12" y1="1.5" x2="12" y2="4" />
            <line x1="12" y1="20" x2="12" y2="22.5" />
            <line x1="1.5" y1="12" x2="4" y2="12" />
            <line x1="20" y1="12" x2="22.5" y2="12" />
            <line x1="4.6" y1="4.6" x2="6.3" y2="6.3" />
            <line x1="17.7" y1="17.7" x2="19.4" y2="19.4" />
            <line x1="4.6" y1="19.4" x2="6.3" y2="17.7" />
            <line x1="17.7" y1="6.3" x2="19.4" y2="4.6" />
          </svg>
        </button>

        <button
          onClick={() => onThemeChange("dark")}
          aria-label="Dark theme"
          aria-pressed={isDark}
          style={{
            border: "none",
            background: isDark ? theme.card : "transparent",
            boxShadow: isDark ? activeShadow : "none",
            width: 30,
            height: 30,
            borderRadius: 8,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill={isDark ? theme.text : theme.textMuted}
            stroke="none"
          >
            <path d="M20.5 14.5A8.5 8.5 0 0 1 9.5 3.5a9 9 0 1 0 11 11Z" />
          </svg>
        </button>
      </div>
    </div>
  );
}
