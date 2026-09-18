/**
 * The studio's single HTTP entry point.
 *
 * Every request the UI makes goes through :func:`apiFetch`, so error handling,
 * base-URL resolution, query building and JSON/FormData encoding are decided in
 * exactly one place. Feature modules in this folder own the *paths and payload
 * shapes*; they never call ``fetch`` themselves.
 *
 * Two rules the rest of the studio relies on:
 *
 * * ``body`` is JSON-encoded unless it is a ``FormData`` (file uploads), so a
 *   caller passes a plain object and cannot forget the ``Content-Type`` header.
 * * A non-2xx response raises :class:`ApiError` carrying the backend's ``detail``
 *   (FastAPI's envelope) rather than a bare status code, because the UI shows
 *   that message to the operator.
 */

/** The API origin. Empty means "same origin", which is how the proxy is used. */
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

/** A value that can appear in a query string. */
export type QueryValue = string | number | boolean | null | undefined;

/** Raised for any non-2xx response. */
export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;

  constructor(status: number, detail: unknown) {
    super(ApiError.describe(status, detail));
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }

  /** Turn FastAPI's ``{"detail": ...}`` envelope into a readable message. */
  private static describe(status: number, detail: unknown): string {
    if (typeof detail === "string" && detail) return detail;
    if (detail) return JSON.stringify(detail);
    return `HTTP ${status}`;
  }
}

/**
 * Build ``?a=1&b=2`` from defined values.
 *
 * ``undefined`` and ``null`` are dropped instead of being sent as the strings
 * ``"undefined"``/``"null"``, which the backend would reject as bad input.
 */
export function buildQuery(params: Record<string, QueryValue>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  const rendered = search.toString();
  return rendered ? `?${rendered}` : "";
}

/** Options accepted by :func:`apiFetch`. */
export interface RequestOptions
  extends Omit<RequestInit, "body" | "method"> {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  /** JSON-serialised, unless it is a ``FormData`` (sent as multipart). */
  body?: unknown;
  /** Appended to the path as a query string. */
  query?: Record<string, QueryValue>;
}

function encodeBody(body: RequestOptions["body"]): {
  payload: BodyInit | undefined;
  headers: Record<string, string>;
} {
  if (body === undefined) return { payload: undefined, headers: {} };
  if (typeof FormData !== "undefined" && body instanceof FormData) {
    // The browser sets the multipart boundary itself; setting the header here
    // would produce a request the server cannot parse.
    return { payload: body, headers: {} };
  }
  return {
    payload: JSON.stringify(body),
    headers: { "Content-Type": "application/json" },
  };
}

async function request<T>(
  path: string,
  { method = "GET", body, query, headers, ...init }: RequestOptions = {},
  parse: (response: Response) => Promise<T>
): Promise<T> {
  const { payload, headers: bodyHeaders } = encodeBody(body);
  const response = await fetch(`${API_BASE}${path}${buildQuery(query ?? {})}`, {
    ...init,
    method,
    body: payload,
    headers: { ...bodyHeaders, ...(headers as Record<string, string>) },
  });

  if (!response.ok) {
    throw new ApiError(response.status, await readDetail(response));
  }
  return parse(response);
}

/** Read FastAPI's error body without letting a malformed one mask the status. */
async function readDetail(response: Response): Promise<unknown> {
  try {
    const parsed = (await response.json()) as { detail?: unknown };
    return parsed?.detail ?? parsed;
  } catch {
    return response.statusText;
  }
}

/** Perform a request and return the parsed JSON body. */
export function apiFetch<T>(path: string, options?: RequestOptions): Promise<T> {
  return request(path, options, (response) => response.json() as Promise<T>);
}

/** Perform a request and return the body as text (``brief.md``, for instance). */
export function apiText(path: string, options?: RequestOptions): Promise<string> {
  return request(path, options, (response) => response.text());
}

/** Perform a request whose body we deliberately ignore (204-style endpoints). */
export function apiSend(path: string, options?: RequestOptions): Promise<void> {
  return request(path, options, async () => undefined);
}
