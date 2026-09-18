const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "";

export async function fetchApi<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    let errorDetail = response.statusText;
    try {
      const err = await response.json();
      errorDetail = err.detail || JSON.stringify(err);
    } catch {
      // ignore
    }
    throw new Error(`API error (${response.status}): ${errorDetail}`);
  }

  return response.json();
}
