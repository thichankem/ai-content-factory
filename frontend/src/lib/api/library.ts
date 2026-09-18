/**
 * Document corpus and library endpoints.
 *
 * Two different searches live here and they are not interchangeable:
 *
 * * ``/documents/search`` queries the *federated* scholarly sources (arXiv,
 *   Crossref, Gutenberg, Open Library, Wikipedia, Internet Archive) and returns
 *   results to download into the local corpus;
 * * ``/library/search`` queries the *local* corpus — the PDFs already downloaded
 *   and indexed with SQLite FTS5 — and returns page-level hits with snippets.
 */

import * as api from "./client";
import { LibraryHit, LibraryResponse } from "@/types/library";
import { DocumentResult } from "@/types/research";

/** ``GET /documents/search`` — federated search across the six public sources. */
export function searchDocuments(q: string, limit = 10): Promise<DocumentResult[]> {
  return api.apiFetch<DocumentResult[]>("/documents/search", {
    query: { q, limit },
  });
}

/** ``GET /library/search`` — full-text search over the local corpus. */
export function searchLibrary(q: string, limit = 20): Promise<LibraryHit[]> {
  return api.apiFetch<LibraryHit[]>("/library/search", {
    query: { q, limit },
  });
}

/** ``GET /library`` — the indexed documents plus corpus counters. */
export function getLibrary(): Promise<LibraryResponse> {
  return api.apiFetch<LibraryResponse>("/library");
}