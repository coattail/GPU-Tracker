import unittest

from gpu_monitor.normalize import normalize_gpu_model


class NormalizeGpuModelTests(unittest.TestCase):
    def test_normalizes_tracked_models(self):
        self.assertEqual(normalize_gpu_model("NVIDIA H100 SXM"), "H100")
        self.assertEqual(normalize_gpu_model("h200"), "H200")
        self.assertEqual(normalize_gpu_model("NVIDIA B200"), "B200")
        self.assertEqual(normalize_gpu_model("NVIDIA B300"), "B300")
        self.assertEqual(normalize_gpu_model("A100 80GB PCIe"), "A100 80GB")
        self.assertEqual(normalize_gpu_model("L40S"), "L40S")
        self.assertEqual(normalize_gpu_model("NVIDIA GeForce RTX 4090"), "RTX 4090")
        self.assertEqual(normalize_gpu_model("RTX_5090"), "RTX 5090")

    def test_rejects_untracked_models(self):
        self.assertIsNone(normalize_gpu_model("A100 40GB"))
        self.assertIsNone(normalize_gpu_model("RTX 4080"))
