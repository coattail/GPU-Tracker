// Run against the local server with playwright-cli run-code "$(cat tests/browser/chart-refresh.js)".
async (page) => {
  const base = 'http://127.0.0.1:4176';
  const snapshot = await (await page.request.get(`${base}/data/aggregated/prices.json`)).json();
  const results = [];
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  for (const path of ['index.html', 'gpu.html?model=H100&range=90D']) {
    for (const scenario of ['changed', 'unchanged', 'failure']) {
      let release;
      const gate = new Promise(resolve => { release = resolve; });
      await page.route('https://www.mercatus-ai.com/api/gpu/trend**', async route => {
        await gate;
        if (scenario === 'failure') return route.abort();
        const requestUrl = new URL(route.request().url());
        if (requestUrl.searchParams.get('range') !== 'ALL') throw new Error('Live requests must include all history');
        const key = requestUrl.searchParams.get('baseModel');
        const model = snapshot.meta.tracked_gpu_models.find(model => model.replaceAll(' ', '_') === key);
        const rows = snapshot.benchmark_series[model];
        return route.fulfill({ json: { success: true, data: rows.map((row, index) => ({
          fetchDate: row.date,
          currentPrice: row.value + (scenario === 'changed' && index === rows.length - 1 ? 0.5 : 0)
        })) } });
      });
      await page.goto(`${base}/${path}`);
      const expectedCount = path === 'index.html' ? snapshot.meta.tracked_gpu_models.length + 1 : 1;
      await page.waitForFunction(count => window.Chart && Object.keys(Chart.instances).length === count, expectedCount);
      await page.evaluate(() => {
        window.savedCharts = Object.values(Chart.instances);
        window.savedCanvases = [...document.querySelectorAll('canvas')];
        window.updateModes = [];
        for (const chart of savedCharts) {
          const update = chart.update;
          chart.update = function(mode) { updateModes.push(mode); return update.call(this, mode); };
        }
        window.cachedPrice = savedCharts[0].data.datasets[0].data.at(-1);
      });
      // Also cover changing the range while live requests are still pending.
      await page.getByRole('button', { name: '7D', exact: true }).click();
      release();
      await page.waitForFunction(() => dashboardData.meta.refresh_mode !== 'cached');
      const state = await page.evaluate(() => ({
        sameCharts: savedCharts.every(chart => Chart.instances[chart.id] === chart),
        sameCanvases: savedCanvases.every((canvas, index) => document.querySelectorAll('canvas')[index] === canvas),
        modes: updateModes,
        delta: savedCharts[0].data.datasets[0].data.at(-1) - cachedPrice,
        count: Object.keys(Chart.instances).length,
        range: activeRange,
        points: savedCharts[0].data.labels.length,
        tickLimit: savedCharts[0].options.scales.x.ticks.maxTicksLimit
      }));
      if (!state.sameCharts || !state.sameCanvases || state.count !== expectedCount ||
          state.range !== '7D' || state.points > 8 ||
          !state.modes.length || state.modes.some(mode => mode !== 'none') ||
          Math.abs(state.delta - (scenario === 'changed' ? 0.5 : 0)) > 1e-9 ||
          (path !== 'index.html' && state.tickLimit !== 8)) {
        throw new Error(`${path} ${scenario}: ${JSON.stringify(state)}`);
      }
      if (path !== 'index.html') {
        await page.setViewportSize({ width: 390, height: 844 });
        await page.waitForFunction(() => !!document.getElementById('chartLegendBox').style.left);
        await page.setViewportSize({ width: 1280, height: 900 });
      }
      await page.getByRole('button', { name: 'MAX', exact: true }).click();
      const fullHistory = await page.evaluate(() => Object.values(Chart.instances).map(chart => ({
        model: chart.canvas.id === 'comparisonChart' ? 'H100' : chart.canvas.closest('.model-card')?.dataset.model || activeModel,
        first: chart.data.labels[0], count: chart.data.labels.length
      })));
      const expectedRows = snapshot.benchmark_series.H100;
      if (fullHistory.some(chart => {
        const rows = snapshot.benchmark_series[chart.model];
        return chart.first !== rows[0].date || chart.count !== rows.length;
      })) {
        throw new Error(`MAX history incomplete: ${JSON.stringify(fullHistory)}`);
      }
      if (path === 'index.html') {
        const coverage = await page.locator('#historyCoverage').textContent();
        if (!coverage.includes(expectedRows[0].date)) throw new Error(`Missing coverage: ${coverage}`);
      } else {
        const notes = await page.locator('#detailNotes').textContent();
        if (!notes.includes(expectedRows[0].date)) throw new Error(`Missing history note: ${notes}`);
      }
      results.push({ path, scenario, chartInstancesRetained: state.count, delta: state.delta, fullHistory });
      await page.unroute('https://www.mercatus-ai.com/api/gpu/trend**');
    }
  }
  if (errors.length) throw new Error(errors.join('\n'));
  return results;
}
