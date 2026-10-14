"""Load the pipeline configuration and resolve repository paths."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
FIGURES = ROOT / "results" / "figures"
TABLES = ROOT / "results" / "tables"


@lru_cache(maxsize=1)
def load(path: Path | None = None) -> dict[str, Any]:
    with open(path or ROOT / "config.yaml") as f:
        cfg = yaml.safe_load(f)
    first, last = cfg["years"]
    cfg["year_list"] = list(range(first, last + 1))
    return cfg


def ensure_dirs() -> None:
    for d in (RAW, PROCESSED, FIGURES, TABLES):
        d.mkdir(parents=True, exist_ok=True)
