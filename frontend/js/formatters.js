const STATUS_LABELS = {
  PUBLISHED: "Published",
  CONFIDENTIAL: "Confidential",
  SUPPRESSED: "Suppressed",
  UNAVAILABLE: "Unavailable",
  UNAVAILABLE_INPUT: "Required input unavailable",
  NOT_MEANINGFUL_BASE: "Prior-year base not meaningful",
  INVALID_DUPLICATE: "Ambiguous source observation",
  INVALID_VALUE: "Invalid source observation",
};

export function statusLabel(status) {
  return STATUS_LABELS[status] || status.replaceAll("_", " ").toLowerCase();
}

export function statusTone(status) {
  if (status === "PUBLISHED") return "published";
  if (status === "CONFIDENTIAL" || status === "SUPPRESSED") return "protected";
  if (status.startsWith("INVALID")) return "invalid";
  return "unavailable";
}

export function directionClass(value) {
  if (value > 0) return "positive";
  if (value < 0) return "negative";
  return "neutral";
}

export function formatNumber(value, { signed = false } = {}) {
  const formatted = new Intl.NumberFormat("en-NZ", {
    maximumFractionDigits: 2,
    minimumFractionDigits: Number.isInteger(value) ? 0 : 2,
  }).format(value);
  return signed && value > 0 ? `+${formatted}` : formatted;
}

export function presentMetric(observation, { signed = false } = {}) {
  if (
    observation.metricStatus !== "PUBLISHED"
    || observation.metricValue === null
    || !Number.isFinite(observation.metricValue)
  ) {
    return {
      available: false,
      text: statusLabel(observation.metricStatus),
      tone: statusTone(observation.metricStatus),
      direction: "neutral",
    };
  }
  return {
    available: true,
    text: formatNumber(observation.metricValue, { signed }),
    tone: "published",
    direction: directionClass(observation.metricValue),
  };
}
