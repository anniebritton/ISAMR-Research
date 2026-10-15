"""Snow-off and degree-day rules on hand-built daily series."""

import numpy as np
import pytest
import pandas as pd

from wapusk_greenup import drivers


def test_snow_off_is_day_after_last_snowy_day():
    doy = np.arange(60, 213)
    depth = np.where(doy <= 140, 20.0, 0.0)
    depth[doy == 150] = 3.0  # late storm counts
    assert drivers.snow_off_last_day(doy, depth, 2, (60, 212)) == 151


def test_snow_off_nan_without_snow():
    doy = np.arange(60, 213)
    assert np.isnan(drivers.snow_off_last_day(doy, np.zeros_like(doy, float), 2, (60, 212)))


def test_tdd_sums_positive_degrees_in_window():
    dates = pd.date_range("2010-01-01", "2010-12-31")
    t = pd.DataFrame({"date": dates, "tc": np.where(dates.dayofyear % 2 == 0, 2.0, -3.0)})
    out = drivers.tdd(t, "tc", (91, 151))
    n_even = sum(d % 2 == 0 for d in range(91, 152))
    assert out.loc[0, "tdd_tc"] == 2.0 * n_even


def test_calibration_fills_only_gaps():
    target = pd.Series([1.0, 2.0, np.nan, 4.0, 5.0, 6.0])
    source = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0, 60.0])
    filled, used = drivers._calibrate(target, source)
    assert used
    assert filled[2] == pytest.approx(3.0)
    assert (filled.drop(2) == target.drop(2)).all()
