import assert from "node:assert/strict";
import test from "node:test";

import {
  directionClass,
  presentMetric,
  statusLabel,
  statusTone,
} from "../js/formatters.js";

test("published signed values preserve positive and negative direction", () => {
  const positive = presentMetric(
    { metricStatus: "PUBLISHED", metricValue: 5.125 },
    { signed: true },
  );
  const negative = presentMetric(
    { metricStatus: "PUBLISHED", metricValue: -1806 },
    { signed: true },
  );

  assert.equal(positive.text, "+5.13");
  assert.equal(positive.direction, "positive");
  assert.equal(negative.text, "-1,806");
  assert.equal(negative.direction, "negative");
  assert.equal(directionClass(0), "neutral");
});

test("protected and unavailable nulls render status text rather than zero", () => {
  for (const [status, label] of [
    ["CONFIDENTIAL", "Confidential"],
    ["SUPPRESSED", "Suppressed"],
    ["UNAVAILABLE", "Unavailable"],
    ["UNAVAILABLE_INPUT", "Required input unavailable"],
    ["NOT_MEANINGFUL_BASE", "Prior-year base not meaningful"],
  ]) {
    const result = presentMetric({ metricStatus: status, metricValue: null });
    assert.equal(result.available, false);
    assert.equal(result.text, label);
    assert.notEqual(result.text, "0");
  }
  assert.equal(statusTone("CONFIDENTIAL"), "protected");
  assert.equal(statusTone("INVALID_VALUE"), "invalid");
  assert.equal(statusLabel("UNAVAILABLE_INPUT"), "Required input unavailable");
});
