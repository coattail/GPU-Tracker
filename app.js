let dashboardData;
let comparisonChart;
let activeRange = "90D";
const miniCharts = new Map();
const SINGLE_SERIES_COLOR = "#dbeafe";

const MODEL_COLORS = {
  H100: "#dbeafe",
  H200: "#fbbf24",
  B200: "#f97316",
  B300: "#fb7185",
  "A100 80GB": "#34d399",
  L40S: "#a78bfa",
};

const RANGE_DAYS = { "7D": 7, "30D": 30, "90D": 90 };

function formatUsd(value) {
  if (!Number.isFinite(value)) return "--";
  return `$${value.toFixed(value >= 10 ? 2 : 3)}`;
}

function formatAxisUsd(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return value;
  return `$${numeric.toFixed(2).replace(/\.?0+$/, "")}`;
}

function formatPct(value) {
  if (!Number.isFinite(value)) return "--";
  const sign = value >= 0 ? "+" : "";
  return `${sign}${(value * 100).toFixed(1)}%`;
}

function latestPoint(rows) {
  return rows?.length ? rows[rows.length - 1] : null;
}

function earliestPoint(rows) {
  return rows?.length ? rows[0] : null;
}

function rangePoints(points, range = activeRange) {
  const count = RANGE_DAYS[range] ?? RANGE_DAYS["90D"];
  return points.slice(-Math.min(points.length, count + 1));
}

function pointStats(points) {
  if (!points.length) return null;
  const values = points.map((point) => point.value);
  const latest = latestPoint(points);
  const earliest = earliestPoint(points);
  return {
    start: earliest,
    end: latest,
    min: Math.min(...values),
    max: Math.max(...values),
    avg: values.reduce((sum, value) => sum + value, 0) / values.length,
    change: latest.value - earliest.value,
    changePct: earliest.value ? (latest.value - earliest.value) / earliest.value : null,
  };
}

function commonChartOptions({ compact = false } = {}) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: "index", intersect: false },
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label(context) {
            return context.dataset.label === "Mercatus GPU Index"
              ? `租金指数: ${formatUsd(context.raw)}`
              : `${context.dataset.label}: ${formatUsd(context.raw)}`;
          },
        },
      },
    },
    scales: {
      x: {
        ticks: { color: "#91a2bd", maxTicksLimit: compact ? 6 : 10 },
        grid: { color: "rgba(255,255,255,0.08)", borderDash: [3, 3] },
      },
      y: {
        position: "right",
        ticks: {
          color: "#91a2bd",
          callback: (value) => formatAxisUsd(value),
        },
        grid: { color: "rgba(255,255,255,0.08)", borderDash: [3, 3] },
      },
    },
  };
}

function createLineChart(canvas, points, { compact = false } = {}) {
  const labels = points.map((point) => point.date);
  const values = points.map((point) => point.value);
  return new Chart(canvas, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Mercatus GPU Index",
          data: values,
          borderColor: SINGLE_SERIES_COLOR,
          backgroundColor: compact ? "rgba(30, 64, 175, 0.22)" : "rgba(30, 64, 175, 0.26)",
          fill: true,
          borderWidth: compact ? 2 : 2.3,
          pointRadius: compact ? 0 : 2,
          pointHoverRadius: 4,
          tension: 0.14,
        },
      ],
    },
    options: commonChartOptions({ compact }),
  });
}

function createComparisonChart(canvas) {
  const labels = rangePoints(dashboardData.benchmark_series.H100 || []).map((point) => point.date);
  const datasets = dashboardData.meta.tracked_gpu_models.map((model) => {
    const points = rangePoints(dashboardData.benchmark_series[model] || []);
    const byDate = new Map(points.map((point) => [point.date, point.value]));
    return {
      label: model,
      data: labels.map((date) => byDate.get(date) ?? null),
      borderColor: MODEL_COLORS[model],
      backgroundColor: MODEL_COLORS[model],
      borderWidth: 2,
      pointRadius: 0,
      pointHoverRadius: 4,
      tension: 0.14,
      fill: false,
    };
  });
  return new Chart(canvas, {
    type: "line",
    data: { labels, datasets },
    options: {
      ...commonChartOptions(),
      plugins: {
        ...commonChartOptions().plugins,
        legend: { labels: { color: "#eef4ff", boxWidth: 10, boxHeight: 10 } },
      },
    },
  });
}

function modelTicker(model) {
  return model.replace(/\s+/g, "").toUpperCase();
}

function renderModelGrid() {
  const grid = document.getElementById("modelChartGrid");
  grid.innerHTML = "";
  miniCharts.forEach((chart) => chart.destroy());
  miniCharts.clear();

  dashboardData.meta.tracked_gpu_models.forEach((model) => {
    const points = rangePoints(dashboardData.benchmark_series[model] || []);
    const stats = pointStats(points);
    const card = document.createElement("article");
    card.className = "terminal-frame model-card";
    card.dataset.model = model;
    card.innerHTML = `
      <div class="ticker-strip">
        <span>${modelTicker(model)}</span>
        <span>${activeRange}</span>
      </div>
      <div class="model-card-head">
        <div>
          <h3>${model}</h3>
        </div>
        <div>
          <div class="model-price">${formatUsd(stats?.end.value)}</div>
          <p class="chart-note ${stats?.change >= 0 ? "up" : "down"}">
            ${stats ? `${formatUsd(stats.change)} · ${formatPct(stats.changePct)}` : "--"}
          </p>
        </div>
      </div>
      <div class="mini-chart-wrap"><canvas></canvas></div>
      <div class="mini-stats">
        <span>H ${formatUsd(stats?.max)}</span>
        <span>L ${formatUsd(stats?.min)}</span>
        <span>AVG ${formatUsd(stats?.avg)}</span>
      </div>
    `;
    card.addEventListener("click", () => {
      window.location.href = `gpu.html?model=${encodeURIComponent(model)}&range=${encodeURIComponent(activeRange)}`;
    });
    grid.append(card);
    miniCharts.set(model, createLineChart(card.querySelector("canvas"), points, { compact: true }));
  });
}

function renderComparison() {
  if (comparisonChart) comparisonChart.destroy();
  comparisonChart = createComparisonChart(document.getElementById("comparisonChart"));

  const ranked = dashboardData.meta.tracked_gpu_models
    .map((model) => {
      const stats = pointStats(rangePoints(dashboardData.benchmark_series[model] || []));
      return { model, stats };
    })
    .filter((item) => item.stats)
    .sort((a, b) => b.stats.changePct - a.stats.changePct);

  document.getElementById("comparisonWindow").textContent = ranked.length
    ? `${ranked[0].stats.start.date} → ${ranked[0].stats.end.date}`
    : "暂无数据";

  document.getElementById("rankingTable").innerHTML = ranked
    .map((item, index) => `
      <div class="ranking-row">
        <span>${index + 1}</span>
        <strong>${item.model}</strong>
        <em>${formatUsd(item.stats.end.value)}</em>
        <b class="${item.stats.changePct >= 0 ? "up" : "down"}">${formatPct(item.stats.changePct)}</b>
      </div>
    `)
    .join("");

  const current = Object.fromEntries(
    dashboardData.meta.tracked_gpu_models.map((model) => [model, latestPoint(rangePoints(dashboardData.benchmark_series[model] || []))?.value])
  );
  const premiums = [
    { label: "B200 / H100", value: current.B200 / current.H100 },
    { label: "B300 / H100", value: current.B300 / current.H100 },
    { label: "H200 / H100", value: current.H200 / current.H100 },
    { label: "H100 / A100 80GB", value: current.H100 / current["A100 80GB"] },
    { label: "H100 / L40S", value: current.H100 / current.L40S },
  ];
  document.getElementById("premiumCards").innerHTML = premiums
    .map((item) => `
      <article class="premium-card nested-card">
        <span>${item.label}</span>
        <strong>${Number.isFinite(item.value) ? `${item.value.toFixed(2)}x` : "--"}</strong>
      </article>
    `)
    .join("");
}

function updateRange(range) {
  activeRange = range;
  document.getElementById("heroRange").textContent = `区间：${range}`;
  document.querySelectorAll(".range-switch button").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.range === range);
  });
  renderModelGrid();
  renderComparison();
}

async function init() {
  const response = await fetch("data/aggregated/prices.json");
  dashboardData = await response.json();
  const firstSeries = dashboardData.benchmark_series[dashboardData.meta.tracked_gpu_models[0]] || [];
  document.getElementById("lastUpdated").textContent = firstSeries.length
    ? `最近刷新：${latestPoint(firstSeries).date}`
    : "暂无刷新数据";
  document.querySelectorAll(".range-switch button").forEach((button) => {
    button.addEventListener("click", () => updateRange(button.dataset.range));
  });
  updateRange(activeRange);
}

init().catch((error) => {
  document.body.innerHTML = `<main class="page-shell"><section class="terminal-frame" style="padding:20px"><h1>数据加载失败</h1><p>${error.message}</p></section></main>`;
});
