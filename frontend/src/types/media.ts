/** Universal media library contract — mirrors ``models/media.py``. */

/** Broad classification of any uploaded media item. */
export type MediaKind = "video" | "audio" | "image" | "document" | "other";

/** One timed segment of a transcription. */
export interface TranscriptSegment {
  start_seconds: number;
  end_seconds: number;
  text: string;
}

/** A file in the universal media library (`MediaItem`). */
export interface MediaItem {
  id: string;
  filename: string;
  kind: MediaKind;
  mime: string;
  size_bytes: number;
  url: string;
  duration_seconds?: number | null;
  width?: number | null;
  height?: number | null;
  transcription: string;
  transcript_segments: TranscriptSegment[];
  text_content: string;
  language: string;
  source: string;
  created_at: string;
  updated_at: string;
}

/** How aggressively the re-cook pipeline transforms the source. */
export type ReCookMode = "condense" | "expand" | "balanced";

/** Payload for ``POST /media/{id}/recook`` (`ReCookRequest`). */
export interface ReCookRequest {
  new_title?: string;
  language?: string;
  target_seconds?: number;
  mode?: ReCookMode;
  change_music?: boolean;
  script_style?: string;
  platform?: string;
}

/** Outcome of a re-cook run: a brand-new project plus its script. */
export interface ReCookResult {
  media_id: string;
  project_id: string;
  project_name: string;
  new_title: string;
  mode: ReCookMode;
  source_transcript: string;
  script: string;
  estimated_seconds: number;
  status: string;
  created_at: string;
}

/** Payload for ``POST /media/from-url``. */
export interface MediaIngestUrlRequest {
  url: string;
  language?: string;
  extract_audio?: boolean;
}

/** One ranked match against the media library (`SearchHit`). */
export interface MediaSearchHit {
  media_id: string;
  filename: string;
  kind: string;
  score: number;
  snippet: string;
}

/** One near-duplicate pair (`POST /media/dedup`). */
export interface MediaDuplicatePair {
  original: string;
  duplicate: string;
  distance: number;
  similarity: number;
}

/** Payload for ``POST /media/dedup`` (`DedupRequest`). */
export interface DedupRequest {
  media_ids?: string[];
}

/**
 * One card in the media bin.
 *
 * A view model, not a contract: the bin mixes library items (which have a
 * `MediaItem` behind them), client-built slide decks (which have nothing on the
 * server yet) and nothing else. Keeping the display fields in one shape is what
 * lets the grid render one list instead of branching per source — and it is why
 * `MediaItem` is mapped into it rather than being rendered directly.
 */
export interface MediaBinRow {
  id: string;
  name: string;
  type: "video" | "audio" | "image" | "document" | "slide" | "other";
  /** Human-readable size, or a note that it was not measured. */
  size: string;
  /** Human-readable duration, or a note that it was not measured. */
  duration: string;
  /** Where it came from; for a library item this is the backend's `source`. */
  source: string;
}

/** Result of a duplicate sweep. */
export interface DedupResult {
  groups: string[][];
  count: number;
  duplicates: MediaDuplicatePair[];
  checked: number;
  max_distance: number;
}