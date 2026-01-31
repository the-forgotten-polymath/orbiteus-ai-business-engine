/**
 * Build upstream FastAPI URLs for the server-side `/api/*` proxy.
 * Keeps one source of truth with `next.config.js` (BACKEND_URL default).
 */
export function backendBaseUrl(): string {
  return (process.env.BACKEND_URL || "http://localhost:8000").replace(/\/$/, "");
}

/** `segments` from `[[...path]]`, e.g. `['auth','login']` → `/api/auth/login`. */
export function backendApiUrl(segments: string[], search: string): string {
  const base = backendBaseUrl();
  const tail = segments.length ? segments.join("/") : "";
  const path = tail ? `/api/${tail}` : "/api";
  return `${base}${path}${search}`;
}
