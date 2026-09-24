import assert from "node:assert/strict";
import test from "node:test";

import { ApiError, createApiClient } from "../js/api-client.js";

function response(payload, { ok = true, status = 200 } = {}) {
  return {
    ok,
    status,
    async json() {
      return payload;
    },
  };
}

test("API client requests industries and returns only presentation fields", async () => {
  let requestedUrl = "";
  const client = createApiClient("http://api.example/", async (url) => {
    requestedUrl = url;
    return response({
      count: 1,
      industries: [{
        industry_code: "CC",
        industry_name: "Manufacturing",
        aggregation_level: "Level 1",
        available_years: [2024, 2025],
        ignored_server_field: "not-consumed",
      }],
    });
  });

  const industries = await client.industries("Level 1");

  assert.equal(requestedUrl, "http://api.example/api/industries?aggregation_level=Level+1");
  assert.deepEqual(industries, [{
    industryCode: "CC",
    industryName: "Manufacturing",
    aggregationLevel: "Level 1",
    availableYears: [2024, 2025],
  }]);
});

test("metric mapping ignores backend-only fields", async () => {
  const client = createApiClient("http://api.example", async () => response({
    metrics: [{
      year: 2023,
      industry_code: "CC521",
      industry_name: "Basic Chemical Manufacturing",
      aggregation_level: "Level 4",
      metric_id: "M2",
      metric_name: "Surplus before income tax",
      metric_value: null,
      metric_status: "CONFIDENTIAL",
      metric_unit: "NZD millions",
      current_input_status: "CONFIDENTIAL",
      prior_input_status: null,
      server_metadata: { opaque: true },
    }],
  }));

  const metrics = await client.performance("CC521", 2023, "Level 4");

  assert.equal(metrics[0].metricValue, null);
  assert.equal(metrics[0].metricStatus, "CONFIDENTIAL");
  assert.equal("server_metadata" in metrics[0], false);
});

test("HTTP no-data and service failures become safe UI error kinds", async () => {
  const emptyClient = createApiClient("http://api.example", async () => response(
    { error: { message: "No trend data matched the query." } },
    { ok: false, status: 404 },
  ));
  await assert.rejects(
    () => emptyClient.trend("AA", "M1", "Level 1"),
    (error) => error instanceof ApiError && error.kind === "empty",
  );

  const offlineClient = createApiClient("http://api.example", async () => {
    throw new TypeError("network implementation detail");
  });
  await assert.rejects(
    () => offlineClient.health(),
    (error) => (
      error instanceof ApiError
      && error.kind === "unavailable"
      && !error.message.includes("implementation detail")
    ),
  );
});
