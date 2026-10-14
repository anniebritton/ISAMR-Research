"""Integration test against the real Earth Engine backend.

Run with `uv run pytest -m gee`. Requires Earth Engine credentials and `gee_project` in config.yaml.
Skipped by default because it needs network access and credentials.
"""

import numpy as np
import pytest

pytestmark = pytest.mark.gee


@pytest.fixture(scope="module")
def ee_ready():
    from wapusk_greenup import gee

    try:
        gee.initialize()
    except Exception as e:  # no credentials on this machine
        pytest.skip(f"Earth Engine unavailable: {e}")


def test_mod09ga_one_month_matches_sample(ee_ready, monkeypatch):
    from wapusk_greenup import aoi, config, extract

    cfg = config.load()
    monkeypatch.setitem(cfg, "extract_doy", [183, 213])  # July only, to keep the request small
    df, rec = extract.mod09ga_year(2016)
    assert rec["n_images"] == 31
    assert set(df["pixel_id"]) == {p["properties"]["pixel_id"] for p in aoi.load_points()}
    valid = df["ndvi_strict"].dropna()
    assert len(valid) > 0
    assert valid.between(-1, 1).all()
    # Mid-summer tundra NDVI should be well above zero where the strict mask lets it through.
    assert np.median(valid) > 0.3
    # Strict never keeps more observations than lenient.
    assert df["ndvi_strict"].notna().sum() <= df["ndvi_lenient"].notna().sum()


def test_cached_extract_matches_fresh_pull(ee_ready, monkeypatch):
    """Re-extraction determinism within tolerance, against the cached July 2016 values."""
    from wapusk_greenup import config, extract

    cached = extract.load("mod09ga")
    cached = cached[(cached["date"].dt.year == 2016) & (cached["date"].dt.dayofyear.between(183, 213))]
    if cached.empty:
        pytest.skip("no cached 2016 extract")
    cfg = config.load()
    monkeypatch.setitem(cfg, "extract_doy", [183, 213])
    fresh, _ = extract.mod09ga_year(2016)
    m = cached.merge(fresh, on=["pixel_id", "date"], suffixes=("_c", "_f")).dropna(subset=["ndvi_strict_c", "ndvi_strict_f"])
    assert len(m) > 100
    assert np.abs(m["ndvi_strict_c"] - m["ndvi_strict_f"]).max() < 1e-3
