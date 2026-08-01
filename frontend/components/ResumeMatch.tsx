"use client";

import { useRef, useState } from "react";
import type { Theme } from "@/lib/theme";
import { analyzeResume, ApiError, type ResumeAnalysis } from "@/lib/api";
import { Card, CardTitle } from "./ui";

const RADIUS = 32;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

type State =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "done"; result: ResumeAnalysis }
  | { status: "error"; message: string };

/**
 * Builds the note text from the real analysis rather than a fixed string, so
 * it always describes the resume that was actually uploaded.
 */
function buildNote(result: ResumeAnalysis): string {
  const strong = result.matched_skills.slice(0, 3);
  const gaps = result.missing_skills.slice(0, 3);

  if (!strong.length && !gaps.length) return "No overlap found with current demand.";
  if (!strong.length) return `No overlap yet. Consider adding ${gaps.join(", ")}.`;

  const parts = [`Strong match on ${strong.join(", ")}.`];
  if (gaps.length) parts.push(`Consider adding ${gaps.join(", ")}.`);
  return parts.join(" ");
}

export function ResumeMatch({ theme }: { theme: Theme }) {
  const [state, setState] = useState<State>({ status: "idle" });
  const inputRef = useRef<HTMLInputElement>(null);

  async function onFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    // Let the same file be re-picked after an error.
    event.target.value = "";
    if (!file) return;

    setState({ status: "loading" });
    try {
      const result = await analyzeResume(file);
      setState({ status: "done", result });
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : "Something went wrong analyzing that file.";
      setState({ status: "error", message });
    }
  }

  const score = state.status === "done" ? state.result.score : null;
  const buttonLabel =
    state.status === "loading"
      ? "Analyzing…"
      : state.status === "done"
        ? "Re-analyze"
        : "Analyze resume";

  const note =
    state.status === "done"
      ? buildNote(state.result)
      : state.status === "loading"
        ? "Reading your resume…"
        : "Upload a resume to compare it against in-demand skills.";

  const dashArray =
    score != null
      ? `${CIRCUMFERENCE * (score / 100)} ${CIRCUMFERENCE}`
      : `0 ${CIRCUMFERENCE}`;

  return (
    <Card
      theme={theme}
      style={{
        padding: "20px 24px",
        marginBottom: 24,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 24,
        flexWrap: "wrap",
      }}
    >
      <div style={{ maxWidth: 420 }}>
        <CardTitle>Resume match</CardTitle>
        <div style={{ fontSize: 13, color: theme.textMuted, marginTop: 4 }}>
          See how your resume lines up against current demand in this dataset.
        </div>

        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.txt"
          onChange={onFile}
          style={{ display: "none" }}
        />
        <button
          onClick={() => inputRef.current?.click()}
          disabled={state.status === "loading"}
          style={{
            marginTop: 12,
            border: `1px solid ${theme.borderStrong}`,
            background: theme.inputBg,
            color: theme.textStrong,
            fontSize: 13,
            fontWeight: 500,
            padding: "8px 14px",
            borderRadius: 8,
            cursor: state.status === "loading" ? "default" : "pointer",
            fontFamily: "inherit",
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            opacity: state.status === "loading" ? 0.7 : 1,
          }}
        >
          {state.status === "loading" && (
            <span
              style={{
                width: 12,
                height: 12,
                borderRadius: "50%",
                border: `2px solid ${theme.borderStrong}`,
                borderTopColor: theme.accent,
                animation: "jmp-spin 0.7s linear infinite",
                display: "inline-block",
              }}
            />
          )}
          {buttonLabel}
        </button>

        {state.status === "error" && (
          <div
            style={{
              marginTop: 10,
              fontSize: 12.5,
              color: theme.accentStrong,
              maxWidth: 380,
              lineHeight: 1.45,
            }}
            role="alert"
          >
            {state.message}
          </div>
        )}

        <div style={{ fontSize: 11.5, color: theme.textMuted, marginTop: 8 }}>
          PDF or .txt · processed in memory, never stored
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        <div style={{ position: "relative", width: 76, height: 76 }}>
          <svg width="76" height="76" viewBox="0 0 76 76" style={{ transform: "rotate(-90deg)" }}>
            <circle
              cx="38"
              cy="38"
              r={RADIUS}
              fill="none"
              stroke={theme.ringTrack}
              strokeWidth="8"
            />
            <circle
              cx="38"
              cy="38"
              r={RADIUS}
              fill="none"
              stroke={theme.accentSecondary}
              strokeWidth="8"
              strokeLinecap="round"
              strokeDasharray={dashArray}
              style={{ transition: "stroke-dasharray 0.5s ease" }}
            />
          </svg>
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontFamily: "'IBM Plex Mono', monospace",
              fontSize: 15,
              fontWeight: 600,
            }}
          >
            {score != null ? `${score}%` : "—"}
          </div>
        </div>

        <div style={{ fontSize: 12.5, color: theme.textSecondary, maxWidth: 160 }}>
          {note}
        </div>
      </div>
    </Card>
  );
}
