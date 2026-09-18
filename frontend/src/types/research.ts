/** Research contract — mirrors ``models/research.py``. */

/** One cited source behind a research bundle. */
export interface ResearchSource {
  id: string;
  title: string;
  url: string;
  source_type: string;
  summary: string;
  highlights: string[];
  relevance: number;
}

/** Everything the research engine gathered for a topic. */
export interface ResearchBundle {
  topic: string;
  sources: ResearchSource[];
  key_facts: string[];
  notes?: string | null;
  generated_at: string;
}

/** A scholarly / archive document returned by federated search. */
export interface DocumentResult {
  id: string;
  title: string;
  authors: string[];
  year?: number | null;
  abstract: string;
  source: string;
  doi?: string | null;
  pdf_url?: string | null;
  landing_url?: string | null;
  venue?: string | null;
  citations?: number | null;
  is_open_access: boolean;
  score: number;
}
