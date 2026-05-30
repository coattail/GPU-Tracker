from __future__ import annotations

import re
from typing import Optional

TRACKED_GPU_MODELS = ("H100", "H200", "B200", "B300", "A100 80GB", "L40S", "RTX 4090", "RTX 5090")


def normalize_gpu_model(raw: str | None) -> Optional[str]:
    text = (raw or "").upper().replace("_", " ").replace("-", " ")
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return None
    if re.search(r"\bB200\b", text):
        return "B200"
    if re.search(r"\bB300\b", text):
        return "B300"
    if re.search(r"\bH200\b", text):
        return "H200"
    if re.search(r"\bH100\b", text):
        return "H100"
    if re.search(r"\bL40S\b", text):
        return "L40S"
    if re.search(r"\bRTX\s*4090\b|\b4090\b", text):
        return "RTX 4090"
    if re.search(r"\bRTX\s*5090\b|\b5090\b", text):
        return "RTX 5090"
    if re.search(r"\bA100\b", text) and re.search(r"\b80\s*GB\b|\b80G\b", text):
        return "A100 80GB"
    return None
