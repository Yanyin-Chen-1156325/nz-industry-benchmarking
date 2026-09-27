export const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

export function resolveApiBaseUrl(configuredValue) {
  const candidate = configuredValue?.trim() || DEFAULT_API_BASE_URL;
  let parsed;
  try {
    parsed = new URL(candidate);
  } catch {
    throw new Error("FRONTEND_API_BASE_URL must be an absolute HTTP(S) URL.");
  }
  if (!["http:", "https:"].includes(parsed.protocol)) {
    throw new Error("FRONTEND_API_BASE_URL must use HTTP or HTTPS.");
  }
  if (parsed.username || parsed.password || parsed.search || parsed.hash) {
    throw new Error(
      "FRONTEND_API_BASE_URL must not contain credentials, a query, or a fragment.",
    );
  }
  return candidate.replace(/\/+$/, "");
}

export function renderRuntimeConfig(configuredValue) {
  const apiBaseUrl = resolveApiBaseUrl(configuredValue);
  return `window.NZ_BENCHMARKING_CONFIG = ${JSON.stringify({ apiBaseUrl }, null, 2)};\n`;
}
