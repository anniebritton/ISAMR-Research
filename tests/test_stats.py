"""Statistics behave correctly on series with known structure."""

import numpy as np
import pandas as pd
import pytest

from wapusk_greenup import stats


def test_theil_sen_recovers_slope():
    years = np.arange(2001, 2025, dtype=float)
    y = 160 - 0.5 * (years - 2001) + np.random.default_rng(1).normal(0, 1, years.size)
    res = stats.theil_sen(years, y)
    assert res["ci_low"] < -0.5 < res["ci_high"]
    assert res["slope"] == pytest.approx(-0.5, abs=0.15)


def test_mann_kendall_detects_strong_trend_only():
    rng = np.random.default_rng(2)
    assert stats.mann_kendall(np.arange(24) * 1.0 + rng.normal(0, 1, 24))["mk_p"] < 0.001
    assert stats.mann_kendall(rng.normal(0, 1, 24))["mk_p"] > 0.01


def test_mdt_is_monotone_in_noise():
    small, _ = stats.minimum_detectable_trend(sd=3, n=24, sims=200, slopes=np.arange(0.1, 1.51, 0.1))
    large, _ = stats.minimum_detectable_trend(sd=8, n=24, sims=200, slopes=np.arange(0.1, 1.51, 0.1))
    assert small < large


def test_nested_models_flags_irrelevant_second_predictor():
    rng = np.random.default_rng(3)
    x1 = rng.normal(150, 8, 24)
    df = pd.DataFrame({"y": 0.8 * x1 + rng.normal(0, 2, 24), "x1": x1, "x2": rng.normal(0, 1, 24)})
    res = stats.nested_models(df, "y", "x1", "x2", reps=500)
    assert res["h2_p"] < 0.001
    assert res["h3_p"] > 0.05
    assert res["h3_delta_r2_ci_low"] >= -1e-9


def test_commonality_partitions_r2():
    rng = np.random.default_rng(4)
    a = rng.normal(0, 1, 50)
    b = 0.7 * a + rng.normal(0, 0.7, 50)
    df = pd.DataFrame({"y": a + b + rng.normal(0, 1, 50), "a": a, "b": b})
    c = stats.commonality(df, "y", "a", "b")
    assert c["unique_a"] + c["unique_b"] + c["common"] == pytest.approx(c["total"])
