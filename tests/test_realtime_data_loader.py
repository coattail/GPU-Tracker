import pathlib
import subprocess
import textwrap
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def run_node(script: str) -> None:
    subprocess.run(["node", "-e", script], cwd=ROOT, check=True)


class RealtimeDataLoaderTests(unittest.TestCase):
    def test_merges_live_mercatus_points_over_static_history(self):
        script = textwrap.dedent(
            r"""
            const assert = require('assert');
            const loader = require('./data-loader.js');

            const staticPayload = {
              meta: {
                generated_at: '2026-05-20',
                currency: 'USD',
                unit: 'GPU-hour',
                tracked_gpu_models: ['H100'],
                primary_source: 'Mercatus GPU Index',
                source_window: '90D',
                history_mode: 'accumulated'
              },
              benchmark_series: {
                H100: [
                  { date: '2026-05-19', value: 3.4, source: 'Mercatus GPU Index', quality: 'unified_daily' },
                  { date: '2026-05-20', value: 3.3, source: 'Mercatus GPU Index', quality: 'unified_daily' }
                ]
              }
            };

            const fetchFn = async (url) => {
              const href = String(url);
              if (href.startsWith('data/aggregated/prices.json')) {
                return { ok: true, json: async () => staticPayload };
              }
              if (href.includes('mercatus-ai.com/api/gpu/trend') && href.includes('baseModel=H100')) {
                return {
                  ok: true,
                  json: async () => ({
                    success: true,
                    data: [
                      { fetchDate: '2026-05-20T00:00:00.000Z', currentPrice: 3.31 },
                      { fetchDate: '2026-05-21T00:00:00.000Z', currentPrice: 3.21 }
                    ]
                  })
                };
              }
              throw new Error(`unexpected fetch ${href}`);
            };

            (async () => {
              const payload = await loader.loadDashboardData({ fetchFn, cacheBust: () => 'test-cache' });
              assert.strictEqual(payload.meta.generated_at, '2026-05-21');
              assert.strictEqual(payload.meta.refresh_mode, 'realtime');
              assert.deepStrictEqual(
                payload.benchmark_series.H100.map((row) => [row.date, row.value]),
                [['2026-05-19', 3.4], ['2026-05-20', 3.31], ['2026-05-21', 3.21]]
              );
            })().catch((error) => {
              console.error(error);
              process.exit(1);
            });
            """
        )
        run_node(script)

    def test_falls_back_to_static_payload_when_live_fetch_fails(self):
        script = textwrap.dedent(
            r"""
            const assert = require('assert');
            const loader = require('./data-loader.js');

            const staticPayload = {
              meta: {
                generated_at: '2026-05-20',
                tracked_gpu_models: ['H100'],
                primary_source: 'Mercatus GPU Index'
              },
              benchmark_series: {
                H100: [{ date: '2026-05-20', value: 3.3, source: 'Mercatus GPU Index', quality: 'unified_daily' }]
              }
            };

            const fetchFn = async (url) => {
              const href = String(url);
              if (href.startsWith('data/aggregated/prices.json')) {
                return { ok: true, json: async () => staticPayload };
              }
              throw new Error('Mercatus unavailable');
            };

            (async () => {
              const payload = await loader.loadDashboardData({ fetchFn, cacheBust: () => 'test-cache' });
              assert.strictEqual(payload.meta.generated_at, '2026-05-20');
              assert.strictEqual(payload.meta.refresh_mode, 'static_fallback');
              assert.match(payload.meta.realtime_error, /Mercatus unavailable/);
            })().catch((error) => {
              console.error(error);
              process.exit(1);
            });
            """
        )
        run_node(script)

    def test_pages_load_data_loader_before_page_scripts(self):
        for html_file, page_script in [("index.html", "app.js"), ("gpu.html", "gpu.js")]:
            html = (ROOT / html_file).read_text(encoding="utf-8")
            self.assertLess(html.index('src="data-loader.js"'), html.index(f'src="{page_script}"'))


class RefreshWorkflowTests(unittest.TestCase):
    def test_github_action_refreshes_hourly(self):
        workflow = (ROOT / ".github" / "workflows" / "daily-refresh.yml").read_text(encoding="utf-8")
        self.assertIn('cron: "20 * * * *"', workflow)


if __name__ == "__main__":
    unittest.main()
