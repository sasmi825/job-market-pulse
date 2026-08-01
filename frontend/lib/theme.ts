/**
 * Theme tokens ported verbatim from the design prototype's THEMES object
 * (`Job Market Pulse.dc.html`). Values are unchanged — including the oklch
 * colour space — so the built UI matches the prototype exactly.
 */

export type ThemeName = "light" | "dark";

export interface Theme {
  pageBg: string;
  card: string;
  border: string;
  borderStrong: string;
  subtleBg: string;
  rowBorder: string;
  gridLine: string;
  ringTrack: string;
  inputBg: string;
  text: string;
  textStrong: string;
  textSecondary: string;
  textMuted: string;
  accent: string;
  accentStrong: string;
  accentSecondary: string;
  accentAreaFill: string;
  accentBandFill: string;
  neutralDot: string;
  cardShadow: string;
  headerBg: string;
}

export const THEMES: Record<ThemeName, Theme> = {
  light: {
    pageBg: "oklch(0.975 0.004 90)",
    card: "oklch(0.995 0.002 90)",
    border: "oklch(0.91 0.006 90)",
    borderStrong: "oklch(0.87 0.006 90)",
    subtleBg: "oklch(0.94 0.005 90)",
    rowBorder: "oklch(0.95 0.004 90)",
    gridLine: "oklch(0.93 0.005 90)",
    ringTrack: "oklch(0.92 0.006 90)",
    inputBg: "oklch(0.98 0.003 90)",
    text: "oklch(0.22 0.01 90)",
    textStrong: "oklch(0.35 0.01 90)",
    textSecondary: "oklch(0.5 0.01 90)",
    textMuted: "oklch(0.55 0.01 90)",
    accent: "oklch(0.58 0.14 265)",
    accentStrong: "oklch(0.4 0.15 265)",
    accentSecondary: "oklch(0.58 0.13 190)",
    accentAreaFill: "oklch(0.58 0.14 265 / 0.08)",
    accentBandFill: "oklch(0.58 0.14 265 / 0.55)",
    neutralDot: "oklch(0.65 0.006 90)",
    cardShadow:
      "0 1px 2px oklch(0.2 0.02 260 / 0.04), 0 8px 24px oklch(0.2 0.02 260 / 0.05)",
    headerBg: "oklch(0.975 0.004 90 / 0.72)",
  },
  dark: {
    pageBg: "oklch(0.15 0.006 260)",
    card: "oklch(0.19 0.007 260)",
    border: "oklch(0.28 0.008 260)",
    borderStrong: "oklch(0.33 0.009 260)",
    subtleBg: "oklch(0.24 0.008 260)",
    rowBorder: "oklch(0.25 0.007 260)",
    gridLine: "oklch(0.26 0.007 260)",
    ringTrack: "oklch(0.27 0.008 260)",
    inputBg: "oklch(0.22 0.007 260)",
    text: "oklch(0.93 0.004 260)",
    textStrong: "oklch(0.8 0.006 260)",
    textSecondary: "oklch(0.68 0.008 260)",
    textMuted: "oklch(0.58 0.008 260)",
    accent: "oklch(0.68 0.15 265)",
    accentStrong: "oklch(0.75 0.14 265)",
    accentSecondary: "oklch(0.68 0.13 190)",
    accentAreaFill: "oklch(0.68 0.15 265 / 0.14)",
    accentBandFill: "oklch(0.68 0.15 265 / 0.45)",
    neutralDot: "oklch(0.55 0.008 260)",
    cardShadow: "0 1px 2px oklch(0 0 0 / 0.16), 0 10px 28px oklch(0 0 0 / 0.28)",
    headerBg: "oklch(0.15 0.006 260 / 0.72)",
  },
};

/** Shared card chrome — rounded corners, subtle border, soft shadow. */
export function cardStyle(theme: Theme): React.CSSProperties {
  return {
    background: theme.card,
    border: `1px solid ${theme.border}`,
    boxShadow: theme.cardShadow,
    borderRadius: 16,
  };
}
