import pathlib
import subprocess
import textwrap
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def run_frontend_function(source_file, function_name, expression):
    source = (ROOT / source_file).read_text(encoding="utf-8")
    marker = f"function {function_name}"
    start = source.index(marker)
    end = source.index("\n}\n", start) + 3
    script = textwrap.dedent(
        f"""
        {source[start:end]}
        const actual = {expression};
        if (actual !== "A100 80GB") {{
          throw new Error(`expected A100 80GB, got ${{actual}}`);
        }}
        """
    )
    subprocess.run(["node", "-e", script], check=True, cwd=ROOT)


class FrontendLabelTests(unittest.TestCase):
    def test_model_ticker_keeps_space_between_gpu_model_and_memory_capacity(self):
        run_frontend_function("app.js", "modelTicker", 'modelTicker("A100 80GB")')
        run_frontend_function("gpu.js", "modelTicker", 'modelTicker("A100 80GB")')
