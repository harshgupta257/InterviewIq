import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(iso: string | null | undefined, opts: Intl.DateTimeFormatOptions = { dateStyle: "medium" }) {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "—" : new Intl.DateTimeFormat(undefined, opts).format(d);
}

export function formatPct(v: number | null | undefined, digits = 0) {
  return v === null || v === undefined ? "—" : `${v.toFixed(digits)}%`;
}

/** Score band used for wording; numbers are always shown alongside. */
export function scoreBand(pct: number): { label: string; tone: "good" | "ok" | "low" } {
  if (pct >= 80) return { label: "Strong", tone: "good" };
  if (pct >= 60) return { label: "Developing", tone: "ok" };
  return { label: "Needs work", tone: "low" };
}

export const storage = {
  get(key: string): string | null {
    try {
      return window.localStorage.getItem(key);
    } catch {
      return null;
    }
  },
  set(key: string, value: string) {
    try {
      window.localStorage.setItem(key, value);
    } catch {
      /* storage unavailable (private mode / quota) */
    }
  },
  remove(key: string) {
    try {
      window.localStorage.removeItem(key);
    } catch {
      /* ignore */
    }
  },
};

/** Accept only same-site relative paths ("/history?x=1"). Rejects "//host", "/\host",
 * absolute URLs and control characters, which browsers may normalise into other origins. */
export function safeRedirectPath(next: string | null | undefined): string | null {
  if (!next || next.length > 512 || !next.startsWith("/")) return null;
  if (next.startsWith("//") || next.includes("\\")) return null;
  for (const ch of next) if (ch.charCodeAt(0) < 0x20) return null;
  return next;
}
