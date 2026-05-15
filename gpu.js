let dashboardData;
let detailChart;
let activeRange = "90D";
let activeModel;

const SINGLE_SERIES_COLOR = "#dbeafe";
const RANGE_DAYS = { "7D": 7, "30D": 30, "90D": 90, MAX: Infinity };

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
  if (count === Infinity) return points;
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

function createDetailChart(canvas, points) {
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
          backgroundColor: "rgba(30, 64, 175, 0.26)",
          fill: true,
          borderWidth: 2.5,
          pointRadius: 0,
          pointHoverRadius: 4,
          tension: 0.14,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      onResize() {
        requestAnimationFrame(() => positionChartLegend(points));
      },
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label(context) {
              return `租金指数: ${formatUsd(context.raw)}`;
            },
          },
        },
      },
      scales: {
        x: {
          ticks: {
            color: "#9aa7bd",
            maxTicksLimit: activeRange === "7D" ? 8 : 12,
            padding: 10,
          },
          grid: {
            color: "rgba(255,255,255,0.12)",
            borderDash: [3, 3],
            lineWidth: 1,
          },
          border: { color: "rgba(255,255,255,0.2)" },
        },
        y: {
          position: "right",
          ticks: {
            color: "#9aa7bd",
            padding: 10,
            callback: (value) => formatAxisUsd(value),
          },
          grid: {
            color: "rgba(255,255,255,0.12)",
            borderDash: [3, 3],
            lineWidth: 1,
          },
          border: { color: "rgba(255,255,255,0.2)" },
        },
      },
    },
  });
}

function positionChartLegend(points) {
  const legend = document.getElementById("chartLegendBox");
  const chart = detailChart;
  if (!legend || !chart || !points.length) return;

  const { chartArea, scales } = chart;
  if (!chartArea || !scales?.x || !scales?.y) return;

  const width = legend.offsetWidth || 176;
  const height = legend.offsetHeight || 112;
  const margin = 14;
  const xSafety = 18;
  const ySafety = 18;
  const bottomAxisClearance = 28;

  const candidates = [
    {
      name: "top-left",
      left: chartArea.left + margin,
      top: chartArea.top + margin,
      xRange: [chartArea.left, chartArea.left + width + margin + xSafety],
      yRange: [chartArea.top, chartArea.top + height + margin + ySafety],
    },
    {
      name: "top-right",
      left: chartArea.right - width - margin,
      top: chartArea.top + margin,
      xRange: [chartArea.right - width - margin - xSafety, chartArea.right],
      yRange: [chartArea.top, chartArea.top + height + margin + ySafety],
    },
    {
      name: "bottom-left",
      left: chartArea.left + margin,
      top: chartArea.bottom - height - margin - bottomAxisClearance,
      xRange: [chartArea.left, chartArea.left + width + margin + xSafety],
      yRange: [chartArea.bottom - height - margin - ySafety - bottomAxisClearance, chartArea.bottom],
    },
    {
      name: "bottom-right",
      left: chartArea.right - width - margin,
      top: chartArea.bottom - height - margin - bottomAxisClearance,
      xRange: [chartArea.right - width - margin - xSafety, chartArea.right],
      yRange: [chartArea.bottom - height - margin - ySafety - bottomAxisClearance, chartArea.bottom],
    },
  ];

  const pixels = points.map((point) => ({
    x: scales.x.getPixelForValue(point.date),
    y: scales.y.getPixelForValue(point.value),
  }));

  const scored = candidates.map((candidate) => {
    const overlapCount = pixels.filter(
      (pixel) =>
        pixel.x >= candidate.xRange[0] &&
        pixel.x <= candidate.xRange[1] &&
        pixel.y >= candidate.yRange[0] &&
        pixel.y <= candidate.yRange[1]
    ).length;
    const cornerBias = candidate.name.startsWith("top") ? 0 : 0.25;
    return { ...candidate, score: overlapCount + cornerBias };
  });

  const best = scored.sort((a, b) => a.score - b.score)[0];
  legend.dataset.position = best.name;
  legend.style.left = `${best.left}px`;
  legend.style.top = `${best.top}px`;
  legend.style.right = "auto";
  legend.style.bottom = "auto";
}

function renderMetrics(points) {
  const stats = pointStats(points);
  const metrics = [
    { label: "最新价", value: formatUsd(stats?.end.value) },
    { label: "区间涨跌", value: stats ? `${formatUsd(stats.change)} · ${formatPct(stats.changePct)}` : "--", tone: stats?.change >= 0 ? "up" : "down" },
    { label: "区间高点", value: formatUsd(stats?.max) },
    { label: "区间低点", value: formatUsd(stats?.min) },
    { label: "区间均价", value: formatUsd(stats?.avg) },
  ];
  document.getElementById("detailMetrics").innerHTML = metrics
    .map((item) => `
      <article class="terminal-frame detail-metric-card">
        <span>${item.label}</span>
        <strong class="${item.tone || ""}">${item.value}</strong>
      </article>
    `)
    .join("");
}

function renderQuoteStrip(points) {
  const stats = pointStats(points);
  const ticker = activeModel.replace(/\s+/g, "").toUpperCase();
  document.getElementById("detailTicker").textContent = ticker;
  document.getElementById("detailChartTicker").textContent = ticker;
  document.getElementById("detailQuotePrice").textContent = formatUsd(stats?.end.value);
  const quoteChange = document.getElementById("detailQuoteChange");
  quoteChange.textContent = stats ? `${formatUsd(stats.change)}  ${formatPct(stats.changePct)}` : "--";
  quoteChange.className = stats?.change >= 0 ? "up" : "down";
  document.getElementById("detailQuoteStats").innerHTML = stats
    ? `
      <span>H ${formatUsd(stats.max)}</span>
      <span>L ${formatUsd(stats.min)}</span>
      <span>AVG ${formatUsd(stats.avg)}</span>
      <span>${stats.start.date} → ${stats.end.date}</span>
    `
    : "";
}

function renderChartLegend(points) {
  const stats = pointStats(points);
  if (!stats) {
    document.getElementById("chartLegendBox").innerHTML = "";
    return;
  }
  document.getElementById("chartLegendBox").innerHTML = `
    <div><span>Last Price</span><strong>${formatUsd(stats.end.value)}</strong></div>
    <div><span>High</span><strong>${formatUsd(stats.max)}</strong></div>
    <div><span>Average</span><strong>${formatUsd(stats.avg)}</strong></div>
    <div><span>Low</span><strong>${formatUsd(stats.min)}</strong></div>
  `;
}

function renderNotes(points) {
  const stats = pointStats(points);
  const h100Points = rangePoints(dashboardData.benchmark_series.H100 || []);
  const h100Latest = latestPoint(h100Points)?.value;
  const premiumToH100 =
    activeModel === "H100" || !Number.isFinite(stats?.end.value) || !Number.isFinite(h100Latest)
      ? null
      : stats.end.value / h100Latest;
  const notes = [
    ["数据源", dashboardData.meta.primary_source],
    ["计价口径", `${dashboardData.meta.currency} / ${dashboardData.meta.unit}`],
    ["当前窗口", `${stats?.start.date ?? "--"} → ${stats?.end.date ?? "--"}`],
    ["样本点数", `${points.length} 点`],
    ["相对 H100", premiumToH100 ? `${premiumToH100.toFixed(2)}x` : "基准型号"],
    ["数据备注", latestPoint(points)?.note || "—"],
  ];
  document.getElementById("detailNotes").innerHTML = notes
    .map(([label, value]) => `
      <div class="detail-note-row">
        <span>${label}</span>
        <strong>${value}</strong>
      </div>
    `)
    .join("");
}

function renderRecentMoves(points) {
  const allPoints = dashboardData.benchmark_series[activeModel] || [];
  const pointIndex = new Map(allPoints.map((point, index) => [point.date, index]));
  const rows = points.slice(-10).map((point) => {
    const index = pointIndex.get(point.date);
    const previous = Number.isInteger(index) && index > 0 ? allPoints[index - 1] : null;
    const change = previous ? point.value - previous.value : null;
    const changePct = previous?.value ? change / previous.value : null;
    return { point, change, changePct };
  });
  document.getElementById("recentMoves").innerHTML = `
    <div class="recent-move-row recent-move-head">
      <span>日期</span>
      <span>价格</span>
      <span>日变动</span>
      <span>日涨跌</span>
    </div>
    ${rows
      .map(
        ({ point, change, changePct }) => `
          <div class="recent-move-row">
            <span>${point.date}</span>
            <strong>${formatUsd(point.value)}</strong>
            <em class="${Number.isFinite(change) ? (change >= 0 ? "up" : "down") : ""}">${Number.isFinite(change) ? formatUsd(change) : "--"}</em>
            <b class="${Number.isFinite(changePct) ? (changePct >= 0 ? "up" : "down") : ""}">${Number.isFinite(changePct) ? formatPct(changePct) : "--"}</b>
          </div>
        `
      )
      .join("")}
  `;
}

function renderDetail() {
  const points = rangePoints(dashboardData.benchmark_series[activeModel] || []);
  const stats = pointStats(points);
  document.getElementById("detailModelTitle").textContent = activeModel;
  document.title = `${activeModel} · GPU 型号详情`;
  document.getElementById("detailLastUpdated").textContent = stats ? `最近刷新：${stats.end.date}` : "暂无刷新数据";
  document.getElementById("detailRangeLabel").textContent = `区间：${activeRange}`;
  document.getElementById("detailHeroCopy").textContent = `${dashboardData.meta.primary_source} · 统一口径 · 自建历史持续累积 · ${dashboardData.meta.currency} / ${dashboardData.meta.unit}`;
  document.getElementById("detailChartTitle").textContent = `${activeModel} 价格走势`;
  document.getElementById("detailChartSubtitle").textContent = stats
    ? `${stats.start.date} → ${stats.end.date} · ${points.length} 点`
    : "暂无数据";

  renderQuoteStrip(points);
  renderMetrics(points);
  renderChartLegend(points);
  renderNotes(points);
  renderRecentMoves(points);
  if (detailChart) detailChart.destroy();
  detailChart = createDetailChart(document.getElementById("detailChart"), points);
  requestAnimationFrame(() => positionChartLegend(points));
}

function updateRange(range) {
  activeRange = range;
  document.querySelectorAll(".range-switch button").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.range === range);
  });
  renderDetail();
}

async function init() {
  const response = await fetch("data/aggregated/prices.json");
  dashboardData = await response.json();
  const params = new URLSearchParams(window.location.search);
  const requestedModel = params.get("model");
  const requestedRange = params.get("range");
  activeModel = dashboardData.meta.tracked_gpu_models.includes(requestedModel)
    ? requestedModel
    : dashboardData.meta.tracked_gpu_models[0];
  activeRange = RANGE_DAYS[requestedRange] ? requestedRange : activeRange;
  document.querySelectorAll(".range-switch button").forEach((button) => {
    button.addEventListener("click", () => updateRange(button.dataset.range));
  });
  updateRange(activeRange);
}

init().catch((error) => {
  document.body.innerHTML = `<main class="page-shell"><section class="terminal-frame" style="padding:20px"><h1>数据加载失败</h1><p>${error.message}</p></section></main>`;
});
