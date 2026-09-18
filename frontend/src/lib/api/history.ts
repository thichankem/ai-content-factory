/**
 * History / anniversary endpoints.
 *
 * These power the "on this day" niche: a curated database of notable events that
 * can seed a project idea without any external call.
 */

import * as api from "@/lib/api/client";
import { OnThisDayEvent } from "@/types/history";

/** ``GET /history/on-this-day`` — today's events, or a specific date's. */
export function onThisDay(params: {
  month?: number;
  day?: number;
} = {}): Promise<OnThisDayEvent[]> {
  return api.apiFetch<OnThisDayEvent[]>("/history/on-this-day", {
    query: params,
  });
}

/** ``GET /history/search`` — search the event database by keyword or location. */
export function searchHistory(q: string): Promise<OnThisDayEvent[]> {
  return api.apiFetch<OnThisDayEvent[]>("/history/search", { query: { q } });
}