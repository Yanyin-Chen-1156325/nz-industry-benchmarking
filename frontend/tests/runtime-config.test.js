import assert from "node:assert/strict";
import test from "node:test";

import {
  DEFAULT_API_BASE_URL,
  renderRuntimeConfig,
  resolveApiBaseUrl,
} from "../scripts/runtime-config.mjs";

test("frontend runtime config defaults to the local API", () => {
  assert.equal(resolveApiBaseUrl(undefined), DEFAULT_API_BASE_URL);
  assert.match(renderRuntimeConfig(undefined), /http:\/\/127\.0\.0\.1:8000/);
});

test("frontend runtime config accepts a cloud API URL", () => {
  const value = "https://api.example.test/base/";

  assert.equal(resolveApiBaseUrl(value), "https://api.example.test/base");
  assert.deepEqual(
    JSON.parse(renderRuntimeConfig(value).match(/= (.*);/s)[1]),
    { apiBaseUrl: "https://api.example.test/base" },
  );
});

test("frontend runtime config rejects unsafe or invalid values", () => {
  for (const value of [
    "relative/path",
    "ftp://api.example.test",
    "https://user:secret@api.example.test",
    "https://api.example.test?token=secret",
    "https://api.example.test#fragment",
  ]) {
    assert.throws(() => resolveApiBaseUrl(value), /FRONTEND_API_BASE_URL/);
  }
});
