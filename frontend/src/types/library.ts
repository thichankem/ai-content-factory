/** Document library contract — mirrors the ``/library`` router. */

/** A hit inside the local document corpus (``LibraryHit``). */
export interface LibraryHit {
  path: string;
  title: string;
  page: number;
  snippet: string;
  score: number;
}

/** Corpus counters shown in the library header (``LibraryStats``). */
export interface LibraryStats {
  database: string;
  documents: number;
  pages: number;
  size_bytes: number;
}

/**
 * ``GET /library``.
 *
 * ``documents`` is what ``list_library()`` returns — a list of dictionaries
 * rather than a model, so only the fields the UI reads are typed.
 */
export interface LibraryResponse {
  documents: Array<Record<string, unknown>>;
  stats: LibraryStats;
}
