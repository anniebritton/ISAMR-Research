"""Baseline extractors recover known crossings on synthetic seasons with gaps and snow."""

import numpy as np
import pytest
from conftest import double_logistic_season

from wapusk_greenup import smoothers


def _observe(doy, ndvi, snow_off, rng, keep_share=0.25, noise=0.02):
    """Snow before snow_off, random cloud gaps after it, Gaussian noise."""
    snow = (doy < snow_off).astype(float)
    obs = ndvi + rng.normal(0, noise, ndvi.size)
    visible = (snow == 0) & (rng.random(doy.size) < keep_share)
    return np.where(visible, obs, np.nan), snow


def _true_crossing(doy, ndvi, base, fraction):
    grid = doy.astype(float)
    return smoothers.crossing(grid, ndvi, base, fraction, 0.05)


@pytest.mark.parametrize("smoother", smoothers.SMOOTHERS)
@pytest.mark.parametrize("fraction", [0.5, 0.15])
def test_recovers_crossing_within_tolerance(smoother, fraction):
    rng = np.random.default_rng(0)
    errors = []
    for mid in (150, 160, 170, 180):
        doy, ndvi = double_logistic_season(mid)
        truth = _true_crossing(doy, ndvi, 0.15, fraction)
        obs, snow = _observe(doy, ndvi, snow_off=mid - 25, rng=rng)
        est = smoothers.greenup_doy(doy, obs, snow, baseline=0.15, smoother=smoother, fraction=fraction)
        errors.append(est - truth)
    assert np.nanmax(np.abs(errors)) < 6
    assert np.mean(np.abs(errors)) < 3


def test_crossing_interpolates_between_days():
    grid = np.arange(100, 110, dtype=float)
    curve = np.array([0.1, 0.1, 0.1, 0.2, 0.4, 0.6, 0.6, 0.6, 0.6, 0.6])
    # Threshold 0.35 sits three quarters of the way from day 103 (0.2) to day 104 (0.4).
    assert smoothers.crossing(grid, curve, 0.1, 0.5, 0.1) == pytest.approx(103.75)


def test_weak_season_is_nan():
    doy, ndvi = double_logistic_season(160, base=0.3, peak=0.35)
    assert np.isnan(smoothers.greenup_doy(doy, ndvi, np.zeros_like(ndvi), baseline=0.3))


def test_too_few_observations_is_nan():
    doy, ndvi = double_logistic_season(160)
    sparse = np.full_like(ndvi, np.nan)
    sparse[::30] = ndvi[::30]
    assert np.isnan(smoothers.greenup_doy(doy, sparse, np.zeros_like(ndvi), baseline=0.15))


def test_left_censored_crossing_is_nan():
    doy, ndvi = double_logistic_season(60)  # already green when the window opens
    assert np.isnan(smoothers.greenup_doy(doy, ndvi, np.zeros_like(ndvi), baseline=0.15))


def test_snow_days_anchor_baseline():
    t, y = smoothers.prepare(np.arange(91, 101), np.r_[[np.nan] * 5, [0.5] * 5], np.r_[[1] * 5, [0] * 5], 0.1)
    assert list(t[:5]) == [91, 92, 93, 94, 95]
    assert np.allclose(y[:5], 0.1)


def test_dormant_baseline_ignores_summer():
    doy = np.r_[np.arange(100, 140), np.arange(160, 240)]
    ndvi = np.r_[np.full(40, 0.12), np.full(80, 0.6)]
    assert smoothers.dormant_baseline(doy, ndvi) == pytest.approx(0.12)
