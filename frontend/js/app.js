import { ApiError, createApiClient } from "./api-client.js";
import { directionClass, presentMetric, statusLabel, statusTone } from "./formatters.js";

const apiBaseUrl = window.NZ_BENCHMARKING_CONFIG?.apiBaseUrl || "http://127.0.0.1:8000";
const api = createApiClient(apiBaseUrl);
const elements = Object.fromEntries(
  [
    "aggregation-level", "industry", "performance-year", "benchmark-year",
    "trend-metric", "benchmark-metric", "ranking-type", "top-n", "api-status",
    "context-year", "context-quality", "selection-summary", "performance-state",
    "performance-content", "primary-metrics", "change-metrics", "trend-state",
    "trend-content", "benchmark-state", "benchmark-content",
  ].map((id) => [id, document.getElementById(id)]),
);

let industries = [];
let selectionGeneration = 0;
let trendGeneration = 0;
let benchmarkGeneration = 0;

function element(tag, className = "", text = "") {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== "") node.textContent = text;
  return node;
}

function currentIndustry() {
  return industries.find((item) => item.industryCode === elements.industry.value);
}

function setLoading(stateNode, contentNode, message) {
  stateNode.className = "state-panel loading";
  stateNode.textContent = message;
  stateNode.hidden = false;
  contentNode.hidden = true;
}

function showError(stateNode, contentNode, error) {
  const message = error instanceof ApiError && error.kind === "empty"
    ? "No matching data is available for this selection."
    : error instanceof ApiError && error.kind === "invalid"
      ? "This selection is not supported. Adjust the filters and try again."
      : "The data service is unavailable. Check that the API is running and try again.";
  stateNode.className = `state-panel ${error?.kind === "empty" ? "empty" : "error"}`;
  stateNode.textContent = message;
  stateNode.hidden = false;
  contentNode.hidden = true;
}

function showContent(stateNode, contentNode) {
  stateNode.hidden = true;
  contentNode.hidden = false;
}

function addOptions(select, items, valueKey, labelBuilder) {
  select.replaceChildren(...items.map((item) => {
    const option = element("option", "", labelBuilder(item));
    option.value = String(item[valueKey]);
    return option;
  }));
  select.disabled = items.length === 0;
}

function populateYears(industry) {
  const years = [...industry.availableYears].sort((left, right) => right - left);
  const items = years.map((year) => ({ year }));
  addOptions(elements["performance-year"], items, "year", (item) => item.year);
  addOptions(elements["benchmark-year"], items, "year", (item) => item.year);
}

async function loadIndustries() {
  const generation = ++selectionGeneration;
  elements.industry.disabled = true;
  elements.industry.replaceChildren(element("option", "", "Loading industries…"));
  try {
    industries = await api.industries(elements["aggregation-level"].value);
    if (generation !== selectionGeneration) return;
    addOptions(
      elements.industry,
      industries,
      "industryCode",
      (item) => `${item.industryCode} — ${item.industryName}`,
    );
    if (!industries.length) throw new ApiError("No industries", { kind: "empty" });
    const defaultIndustry = industries.find((item) => /^[A-Z]/.test(item.industryCode))
      || industries[0];
    elements.industry.value = defaultIndustry.industryCode;
    populateYears(defaultIndustry);
    await refreshSelection();
  } catch (error) {
    if (generation !== selectionGeneration) return;
    elements.industry.replaceChildren(element("option", "", "No industries available"));
    showError(elements["performance-state"], elements["performance-content"], error);
    showError(elements["trend-state"], elements["trend-content"], error);
    showError(elements["benchmark-state"], elements["benchmark-content"], error);
  }
}

function metricCard(observation) {
  const display = presentMetric(observation);
  const card = element("article", "metric-card");
  card.append(
    element("p", "metric-label", observation.metricName),
    element("p", "metric-value", display.text),
    element("p", "metric-unit", display.available ? observation.metricUnit : "No numeric value published"),
    element("span", `status-chip ${display.tone}`, statusLabel(observation.metricStatus)),
  );
  return card;
}

function changeRow(observation) {
  const display = presentMetric(observation, { signed: true });
  const row = element("div", "change-row");
  row.append(
    element("span", "", observation.metricName),
    element("span", `signed-value ${display.direction}`, display.text),
    element("span", `status-chip ${display.tone}`, display.available ? observation.metricUnit : statusLabel(observation.metricStatus)),
  );
  return row;
}

async function loadPerformance(generation) {
  setLoading(elements["performance-state"], elements["performance-content"], "Loading performance…");
  try {
    const metrics = await api.performance(
      elements.industry.value,
      Number(elements["performance-year"].value),
      elements["aggregation-level"].value,
    );
    if (generation !== selectionGeneration) return;
    const primary = metrics.filter((metric) => ["M1", "M2", "M3"].includes(metric.metricId));
    const changes = metrics.filter((metric) => ["M4", "M5", "M6"].includes(metric.metricId));
    elements["primary-metrics"].replaceChildren(...primary.map(metricCard));
    elements["change-metrics"].replaceChildren(...changes.map(changeRow));
    const published = metrics.filter((metric) => metric.metricStatus === "PUBLISHED").length;
    elements["context-year"].textContent = elements["performance-year"].value;
    elements["context-quality"].textContent = `${published} of ${metrics.length} metrics published`;
    showContent(elements["performance-state"], elements["performance-content"]);
  } catch (error) {
    if (generation === selectionGeneration) {
      showError(elements["performance-state"], elements["performance-content"], error);
    }
  }
}

async function loadTrend() {
  const generation = ++trendGeneration;
  setLoading(elements["trend-state"], elements["trend-content"], "Loading trend…");
  try {
    const observations = await api.trend(
      elements.industry.value,
      elements["trend-metric"].value,
      elements["aggregation-level"].value,
    );
    if (generation !== trendGeneration) return;
    const publishedValues = observations
      .filter((item) => item.metricStatus === "PUBLISHED" && item.metricValue !== null)
      .map((item) => Math.abs(item.metricValue));
    const maximum = Math.max(...publishedValues, 1);
    const rows = observations.map((observation) => {
      const display = presentMetric(observation);
      const row = element("div", "trend-row");
      const track = element("div", "trend-bar-track");
      const bar = element("div", "trend-bar");
      bar.style.width = display.available
        ? `${Math.max(2, (Math.abs(observation.metricValue) / maximum) * 100)}%`
        : "0";
      track.append(bar);
      row.append(
        element("span", "trend-year", String(observation.year)),
        track,
        element(
          "span",
          `trend-value ${display.direction}`,
          display.available ? `${display.text} ${observation.metricUnit}` : display.text,
        ),
      );
      return row;
    });
    elements["trend-content"].replaceChildren(...rows);
    showContent(elements["trend-state"], elements["trend-content"]);
  } catch (error) {
    if (generation === trendGeneration) {
      showError(elements["trend-state"], elements["trend-content"], error);
    }
  }
}

function benchmarkTable(results) {
  const table = element("table");
  const head = element("thead");
  const headingRow = element("tr");
  ["Rank", "Industry", "Code", "Change"].forEach((label) => headingRow.append(element("th", "", label)));
  head.append(headingRow);
  const body = element("tbody");
  for (const result of results) {
    const row = element("tr");
    row.append(
      element("td", "", String(result.rankPosition)),
      element("td", "", result.industryName),
      element("td", "", result.industryCode),
      element(
        "td",
        `signed-value ${directionClass(result.metricValue)}`,
        `${presentMetric(result, { signed: true }).text} ${result.metricUnit}`,
      ),
    );
    body.append(row);
  }
  table.append(head, body);
  return table;
}

async function loadBenchmark() {
  const generation = ++benchmarkGeneration;
  setLoading(elements["benchmark-state"], elements["benchmark-content"], "Loading ranking…");
  try {
    const results = await api.benchmarks({
      year: Number(elements["benchmark-year"].value),
      metricId: elements["benchmark-metric"].value,
      aggregationLevel: elements["aggregation-level"].value,
      rankingType: elements["ranking-type"].value,
      topN: Number(elements["top-n"].value),
    });
    if (generation !== benchmarkGeneration) return;
    elements["benchmark-content"].replaceChildren(benchmarkTable(results));
    showContent(elements["benchmark-state"], elements["benchmark-content"]);
  } catch (error) {
    if (generation === benchmarkGeneration) {
      showError(elements["benchmark-state"], elements["benchmark-content"], error);
    }
  }
}

async function refreshSelection() {
  const selected = currentIndustry();
  if (!selected) return;
  const generation = ++selectionGeneration;
  elements["selection-summary"].textContent = `${selected.industryName} · ${elements["aggregation-level"].value}`;
  await Promise.all([loadPerformance(generation), loadTrend(), loadBenchmark()]);
}

async function checkHealth() {
  try {
    await api.health();
    elements["api-status"].className = "api-status online";
    elements["api-status"].lastChild.textContent = " API online";
  } catch {
    elements["api-status"].className = "api-status offline";
    elements["api-status"].lastChild.textContent = " API unavailable";
  }
}

elements["aggregation-level"].addEventListener("change", loadIndustries);
elements.industry.addEventListener("change", () => {
  populateYears(currentIndustry());
  refreshSelection();
});
elements["performance-year"].addEventListener("change", () => {
  const generation = ++selectionGeneration;
  loadPerformance(generation);
});
elements["trend-metric"].addEventListener("change", loadTrend);
for (const id of ["benchmark-year", "benchmark-metric", "ranking-type", "top-n"]) {
  elements[id].addEventListener("change", loadBenchmark);
}

await checkHealth();
await loadIndustries();
