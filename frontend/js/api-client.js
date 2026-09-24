export class ApiError extends Error {
  constructor(message, { kind = "unknown", status = null } = {}) {
    super(message);
    this.name = "ApiError";
    this.kind = kind;
    this.status = status;
  }
}

function queryString(parameters) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(parameters)) {
    if (value !== null && value !== undefined && value !== "") {
      query.set(key, String(value));
    }
  }
  return query.toString();
}

function publicMetric(row) {
  return {
    year: row.year,
    industryCode: row.industry_code,
    industryName: row.industry_name,
    aggregationLevel: row.aggregation_level,
    metricId: row.metric_id,
    metricName: row.metric_name,
    metricValue: row.metric_value,
    metricStatus: row.metric_status,
    metricUnit: row.metric_unit,
    currentInputStatus: row.current_input_status,
    priorInputStatus: row.prior_input_status,
  };
}

async function responseError(response) {
  let message = "The request could not be completed.";
  try {
    const payload = await response.json();
    message = payload?.error?.message || message;
  } catch {
    // A non-JSON upstream response is deliberately reduced to a safe message.
  }
  const kind = response.status === 404
    ? "empty"
    : response.status === 422
      ? "invalid"
      : response.status >= 500
        ? "unavailable"
        : "unknown";
  return new ApiError(message, { kind, status: response.status });
}

export function createApiClient(baseUrl, fetchImplementation = globalThis.fetch) {
  const root = baseUrl.replace(/\/$/, "");

  async function get(path, parameters = {}) {
    const query = queryString(parameters);
    try {
      const response = await fetchImplementation(`${root}${path}${query ? `?${query}` : ""}`, {
        headers: { Accept: "application/json" },
      });
      if (!response.ok) throw await responseError(response);
      return await response.json();
    } catch (error) {
      if (error instanceof ApiError) throw error;
      throw new ApiError("The API is unavailable. Check that it is running and try again.", {
        kind: "unavailable",
      });
    }
  }

  return {
    health: () => get("/api/health"),
    async industries(aggregationLevel) {
      const payload = await get("/api/industries", {
        aggregation_level: aggregationLevel,
      });
      return payload.industries.map((row) => ({
        industryCode: row.industry_code,
        industryName: row.industry_name,
        aggregationLevel: row.aggregation_level,
        availableYears: [...row.available_years],
      }));
    },
    async performance(industryCode, year, aggregationLevel) {
      const payload = await get(
        `/api/industries/${encodeURIComponent(industryCode)}/performance`,
        { year, aggregation_level: aggregationLevel },
      );
      return payload.metrics.map(publicMetric);
    },
    async trend(industryCode, metricId, aggregationLevel) {
      const payload = await get(
        `/api/industries/${encodeURIComponent(industryCode)}/trend`,
        { metric_id: metricId, aggregation_level: aggregationLevel },
      );
      return payload.observations.map(publicMetric);
    },
    async benchmarks({ year, metricId, aggregationLevel, rankingType, topN }) {
      const payload = await get("/api/benchmarks", {
        year,
        metric_id: metricId,
        aggregation_level: aggregationLevel,
        ranking_type: rankingType,
        top_n: topN,
      });
      return payload.results.map((row) => ({
        rankPosition: row.rank_position,
        rankingType: row.ranking_type,
        year: row.year,
        industryCode: row.industry_code,
        industryName: row.industry_name,
        aggregationLevel: row.aggregation_level,
        metricId: row.metric_id,
        metricName: row.metric_name,
        metricValue: row.metric_value,
        metricStatus: row.metric_status,
        metricUnit: row.metric_unit,
      }));
    },
  };
}
