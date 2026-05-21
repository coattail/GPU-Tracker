(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  root.GpuDataLoader = api;
})(typeof globalThis !== "undefined" ? globalThis : window, function () {
  const STATIC_DATA_PATH = "data/aggregated/prices.json";
  const MERCATUS_TREND_URL = "https://www.mercatus-ai.com/api/gpu/trend";
  const MERCATUS_MODEL_MAP = {
    H100: "H100",
    H200: "H200",
    B200: "B200",
    B300: "B300",
    "A100 80GB": "A100_80GB",
    L40S: "L40S",
  };

  function defaultCacheBust() {
    return Date.now().toString();
  }

  function staticDataUrl(cacheBust) {
    return `${STATIC_DATA_PATH}?v=${encodeURIComponent(cacheBust())}`;
  }

  async function fetchJson(fetchFn, url) {
    const response = await fetchFn(url, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Request failed ${response.status || "unknown"}: ${url}`);
    }
    return response.json();
  }

  function normalizeMercatusRows(rows) {
    return (rows || [])
      .filter((row) => row.currentPrice !== null && row.currentPrice !== undefined && row.fetchDate)
      .map((row) => ({
        date: String(row.fetchDate).slice(0, 10),
        value: Number(row.currentPrice),
        source: "Mercatus GPU Index",
        quality: "unified_daily",
        note: "Realtime Mercatus public series",
      }))
      .filter((row) => row.date && Number.isFinite(row.value));
  }

  function trackedModelsFrom(staticPayload) {
    return staticPayload?.meta?.tracked_gpu_models?.length
      ? staticPayload.meta.tracked_gpu_models
      : Object.keys(MERCATUS_MODEL_MAP);
  }

  async function collectMercatusSeries({ fetchFn, models }) {
    const entries = await Promise.all(
      models.map(async (model) => {
        const baseModel = MERCATUS_MODEL_MAP[model];
        if (!baseModel) return [model, []];
        const url = `${MERCATUS_TREND_URL}?range=90D&baseModel=${encodeURIComponent(baseModel)}`;
        const payload = await fetchJson(fetchFn, url);
        if (!payload.success) {
          const message = payload.error?.message || `Mercatus API failed for ${model}`;
          throw new Error(message);
        }
        return [model, normalizeMercatusRows(payload.data)];
      })
    );
    return Object.fromEntries(entries);
  }

  function mergeSeries(staticSeries, liveSeries, models) {
    const merged = {};
    for (const model of models) {
      const byDate = new Map();
      for (const row of staticSeries?.[model] || []) {
        if (row.date) byDate.set(row.date, row);
      }
      for (const row of liveSeries?.[model] || []) {
        if (row.date) byDate.set(row.date, row);
      }
      merged[model] = Array.from(byDate.values()).sort((a, b) => a.date.localeCompare(b.date));
    }
    return merged;
  }

  function latestDate(series) {
    return Object.values(series)
      .flat()
      .map((row) => row.date)
      .filter(Boolean)
      .sort()
      .at(-1) || null;
  }

  function withMeta(staticPayload, benchmarkSeries, refreshMode, extraMeta = {}) {
    return {
      ...staticPayload,
      meta: {
        ...(staticPayload.meta || {}),
        generated_at: latestDate(benchmarkSeries) || staticPayload.meta?.generated_at || null,
        refresh_mode: refreshMode,
        realtime_source: "Mercatus GPU Index",
        ...extraMeta,
      },
      benchmark_series: benchmarkSeries,
    };
  }

  async function loadStaticPayload({ fetchFn, cacheBust }) {
    return fetchJson(fetchFn, staticDataUrl(cacheBust));
  }

  async function loadDashboardData(options = {}) {
    const fetchFn = options.fetchFn || fetch;
    const cacheBust = options.cacheBust || defaultCacheBust;
    const staticPayload = await loadStaticPayload({ fetchFn, cacheBust });
    const models = trackedModelsFrom(staticPayload);

    try {
      const liveSeries = await collectMercatusSeries({ fetchFn, models });
      const benchmarkSeries = mergeSeries(staticPayload.benchmark_series || {}, liveSeries, models);
      return withMeta(staticPayload, benchmarkSeries, "realtime");
    } catch (error) {
      return withMeta(staticPayload, staticPayload.benchmark_series || {}, "static_fallback", {
        realtime_error: error instanceof Error ? error.message : String(error),
      });
    }
  }

  return {
    loadDashboardData,
    collectMercatusSeries,
    mergeSeries,
  };
});
