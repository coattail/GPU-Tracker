import json
import pathlib
import subprocess
import textwrap
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def run_frontend_function(source_file, function_name, expression, expected="A100 80GB"):
    source = (ROOT / source_file).read_text(encoding="utf-8")
    marker = f"function {function_name}"
    start = source.index(marker)
    end = source.index("\n}\n", start) + 3
    script = textwrap.dedent(
        f"""
        {source[start:end]}
        const actual = {expression};
        const expected = {json.dumps(expected)};
        if (actual !== expected) {{
          throw new Error(`expected ${{expected}}, got ${{actual}}`);
        }}
        """
    )
    subprocess.run(["node", "-e", script], check=True, cwd=ROOT)


class FrontendLabelTests(unittest.TestCase):
    def test_model_ticker_keeps_space_between_gpu_model_and_memory_capacity(self):
        run_frontend_function("app.js", "modelTicker", 'modelTicker("A100 80GB")')
        run_frontend_function("gpu.js", "modelTicker", 'modelTicker("A100 80GB")')

    def test_model_cards_show_representative_interval_changes(self):
        source = (ROOT / "app.js").read_text(encoding="utf-8")
        self.assertIn('const REPRESENTATIVE_RANGES = ["7D", "30D", "90D"]', source)
        self.assertIn("pointStats(rangePoints(allPoints, range))?.changePct", source)
        self.assertNotIn("<span>H ${formatUsd(stats?.max)}</span>", source)
        self.assertNotIn("<span>L ${formatUsd(stats?.min)}</span>", source)
        self.assertNotIn("<span>AVG ${formatUsd(stats?.avg)}</span>", source)

    def test_tiny_negative_change_does_not_render_as_negative_zero(self):
        run_frontend_function("app.js", "formatPct", "formatPct(-0.0001)", "0.0%")
        run_frontend_function("gpu.js", "formatPct", "formatPct(-0.0001)", "0.0%")
