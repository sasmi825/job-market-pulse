/** Formatting helpers, matching the prototype's conventions. */

/** `fmtK` from the design: 124780 -> "$125k". */
export function fmtK(n: number): string {
  return "$" + Math.round(n / 1000) + "k";
}

export function fmtRange(min: number | null, max: number | null): string {
  if (min == null && max == null) return "—";
  if (min != null && max != null) {
    return min === max ? fmtK(min) : `${fmtK(min)}–${fmtK(max)}`;
  }
  return fmtK((min ?? max) as number);
}

/** API seniority values are lowercase; the design renders them capitalised. */
export function titleCase(s: string | null | undefined): string {
  if (!s) return "—";
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/** "3d ago" / "Today", from an ISO timestamp. */
export function postedLabel(iso: string | null): string {
  if (!iso) return "—";
  const posted = new Date(iso);
  if (Number.isNaN(posted.getTime())) return "—";
  const days = Math.floor((Date.now() - posted.getTime()) / 86_400_000);
  if (days <= 0) return "Today";
  if (days === 1) return "1d ago";
  return `${days}d ago`;
}

export function formatDateLabel(d: Date): string {
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

/** "Jul 31, 2026 · 6:00 AM PT"-style stamp for the hero. */
export function formatUpdatedAt(d: Date): string {
  const date = d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
  const time = d.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
  });
  return `${date} · ${time}`;
}

/** Compact skills cell: first three, then "+n". */
export function skillsLabel(skills: string[]): string {
  if (!skills.length) return "—";
  const head = skills.slice(0, 3).join(", ");
  return skills.length > 3 ? `${head} +${skills.length - 3}` : head;
}
