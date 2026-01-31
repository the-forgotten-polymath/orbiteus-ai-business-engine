"use client";
/**
 * SSE client for the portal — subscribes to a single shared resource
 * (DoD §12.6).
 *
 * Why a portal-only flavour
 * -------------------------
 * The standard `/api/realtime/subscribe` requires a normal `access`
 * JWT (`scope=internal`) which a portal visitor never has. The
 * backend therefore exposes a parallel `/api/portal/realtime` that
 * authenticates with the share-link token itself and only allows
 * topics that match the resource the token grants access to.
 *
 * Topic shape (mirrors the rest of the backplane):
 *   tenant:{tenant_id}:model:{model}:record:{record_id}
 *
 * Reconnect strategy mirrors `admin-ui/src/lib/realtime.ts`: explicit
 * close + exponential back-off so a 401/403 doesn't loop hot.
 */
import { useEffect, useRef } from "react";

export interface RealtimeMessage {
  event: "record.created" | "record.updated" | "record.deleted";
  model: string;
  record_id: string;
  tenant_id: string;
  actor: string | null;
  request_id: string | null;
  ts: string | null;
  diff: Record<string, [unknown, unknown]> | null;
}

const RECONNECT_DELAY_MS = 3000;
const MAX_RECONNECT_DELAY_MS = 30_000;

export interface UseRealtimeShareResourceArgs {
  /** Share-link JWT — same value the page received in its URL. */
  shareToken: string;
  /** Tenant id from `/api/portal/exchange` response. */
  tenantId: string | null | undefined;
  /** Dotted model name — `"crm.lead"`, `"crm.person"`, … */
  model: string | null | undefined;
  /** Resource id the share grants access to. */
  recordId: string | null | undefined;
}

/**
 * Subscribe to the canonical record topic for a portal-shared resource.
 *
 * No-op until every required argument is set (the page typically has
 * them only after `/api/portal/exchange` resolves).
 */
export function useRealtimeShareResource(
  { shareToken, tenantId, model, recordId }: UseRealtimeShareResourceArgs,
  onChange: (msg: RealtimeMessage) => void,
): void {
  const cbRef = useRef(onChange);
  useEffect(() => {
    cbRef.current = onChange;
  }, [onChange]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!shareToken || !tenantId || !model || !recordId) return;

    const topic = `tenant:${tenantId}:model:${model}:record:${recordId}`;
    const url =
      `/api/portal/realtime?token=${encodeURIComponent(shareToken)}` +
      `&topic=${encodeURIComponent(topic)}`;

    let es: EventSource | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let attempts = 0;
    let cancelled = false;

    function connect() {
      if (cancelled) return;
      es = new EventSource(url);

      es.addEventListener("message", (ev) => {
        try {
          const data = JSON.parse((ev as MessageEvent).data) as RealtimeMessage;
          cbRef.current(data);
        } catch {
          /* malformed payload — ignore */
        }
      });

      es.addEventListener("open", () => {
        attempts = 0;
      });

      es.addEventListener("error", () => {
        es?.close();
        es = null;
        if (cancelled) return;
        attempts += 1;
        const delay = Math.min(
          RECONNECT_DELAY_MS * Math.pow(1.5, attempts - 1),
          MAX_RECONNECT_DELAY_MS,
        );
        reconnectTimer = setTimeout(connect, delay);
      });
    }

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      es?.close();
    };
  }, [shareToken, tenantId, model, recordId]);
}
