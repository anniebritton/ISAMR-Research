"""Annual predictors: snow-off date, thawing degree days, and exploratory covariates.

Both primary predictors are independent of the MODIS snow flag used to build the NDVI series.
Snow-off comes from park-mean ERA5-Land snow cover: the Churchill station omits spring snow-on-ground
reports in 9 of 24 years, and its snow-off agrees with park-wide estimates at only r ~ 0.57 (ERA5-Land vs
MODIS: r ~ 0.81). Thawing degree days come from the Churchill station, which is complete.
Station snow-off (gap-filled from ERA5-Land) and ERA5-Land TDD are sensitivity alternatives;
MODIS NDSI snow-off is a cross-check only.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, extract, station


def _doy(df: pd.DataFrame) -> pd.DataFrame:
    return df.assign(year=df["date"].dt.year, doy=df["date"].dt.dayofyear)


def snow_off_last_day(doy: np.ndarray, value: np.ndarray, threshold: float, window: tuple[int, int]) -> float:
    """Day after the last day in the window with value >= threshold."""
    sel = (doy >= window[0]) & (doy <= window[1]) & (value >= threshold)
    return float(doy[sel].max() + 1) if sel.any() else np.nan


def station_snow_off(st: pd.DataFrame, min_obs_before: int = 20) -> pd.DataFrame:
    """Station snow-off, NaN when the 30 days before it have too few snow-on-ground reports."""
    cfg = config.load()["drivers"]
    rows = []
    for year, g in _doy(st).groupby("year"):
        g = g.dropna(subset=["snow_on_ground_cm"])
        d = snow_off_last_day(g["doy"].to_numpy(), g["snow_on_ground_cm"].to_numpy(), cfg["snow_off_threshold_cm"],
                              tuple(cfg["snow_off_search_doy"]))
        n_before = int(((g["doy"] >= d - 30) & (g["doy"] < d)).sum()) if not np.isnan(d) else 0
        rows.append({"year": year, "snow_off_station": d if n_before >= min_obs_before else np.nan,
                     "snow_off_station_obs30": n_before})
    return pd.DataFrame(rows)


def era5_snow_off(era: pd.DataFrame) -> pd.DataFrame:
    cfg = config.load()["drivers"]
    rows = []
    for year, g in _doy(era).groupby("year"):
        rows.append({"year": year, "snow_off_era5": snow_off_last_day(
            g["doy"].to_numpy(), g["snow_cover"].to_numpy(), cfg["era5_snow_cover_threshold"],
            tuple(cfg["snow_off_search_doy"]))})
    return pd.DataFrame(rows)


def modis_snow_off(snow: pd.DataFrame, ndsi_threshold: float = 40, min_valid: float = 0.5) -> pd.DataFrame:
    """Cross-check only: last day the park-mean NDSI (x100) is at or above 40 on a mostly clear day."""
    cfg = config.load()["drivers"]
    rows = []
    for year, g in _doy(snow).groupby("year"):
        g = g[g["valid_fraction"] >= min_valid]
        rows.append({"year": year, "snow_off_modis": snow_off_last_day(
            g["doy"].to_numpy(), g["ndsi"].to_numpy(), ndsi_threshold, tuple(cfg["snow_off_search_doy"]))})
    return pd.DataFrame(rows)


def _calibrate(target: pd.Series, source: pd.Series) -> tuple[pd.Series, bool]:
    """Fill NaNs in target from a linear fit on years where both exist."""
    both = target.notna() & source.notna()
    if both.sum() < 5:
        return target, False
    slope, intercept = np.polyfit(source[both], target[both], 1)
    filled = target.copy()
    gap = target.isna() & source.notna()
    filled[gap] = intercept + slope * source[gap]
    return filled, bool(gap.any())


def tdd(daily_t: pd.DataFrame, column: str, window: tuple[int, int]) -> pd.DataFrame:
    d = _doy(daily_t)
    d = d[(d["doy"] >= window[0]) & (d["doy"] <= window[1])]
    return d.groupby("year").agg(
        **{f"tdd_{column}": (column, lambda s: s.clip(lower=0).sum()), f"tdd_{column}_n": (column, "count")}
    ).reset_index()


def station_temperature_filled(st: pd.DataFrame, era: pd.DataFrame) -> pd.DataFrame:
    """Station daily mean temperature with gaps filled from ERA5-Land by a daily linear calibration."""
    m = st[["date", "tmean_c"]].merge(era[["date", "t2m_c"]], on="date", how="left")
    both = m["tmean_c"].notna() & m["t2m_c"].notna()
    slope, intercept = np.polyfit(m.loc[both, "t2m_c"], m.loc[both, "tmean_c"], 1)
    gap = m["tmean_c"].isna() & m["t2m_c"].notna()
    m["tmean_filled_c"] = m["tmean_c"]
    m.loc[gap, "tmean_filled_c"] = intercept + slope * m.loc[gap, "t2m_c"]
    m["tmean_was_filled"] = gap
    return m


def run() -> pd.DataFrame:
    cfg = config.load()
    dcfg = cfg["drivers"]
    st = station.load()
    era = extract.load("era5")
    snow = extract.load("mod10a1")
    window = tuple(dcfg["tdd_window_doy"])

    df = pd.DataFrame({"year": cfg["year_list"]})
    df = df.merge(station_snow_off(st), on="year", how="left")
    df = df.merge(era5_snow_off(era), on="year", how="left")
    df = df.merge(modis_snow_off(snow), on="year", how="left")
    df["snow_off"] = df["snow_off_era5"]
    df["snow_off_station_filled"], _ = _calibrate(df["snow_off_station"], df["snow_off_era5"])
    df["snow_off_station_source"] = np.where(df["snow_off_station"].notna(), "station", "era5_calibrated")

    temp = station_temperature_filled(st, era)
    t_station = tdd(temp, "tmean_filled_c", window).rename(columns={"tdd_tmean_filled_c": "tdd", "tdd_tmean_filled_c_n": "tdd_days"})
    filled_days = _doy(temp).query("@window[0] <= doy <= @window[1]").groupby("year")["tmean_was_filled"].sum()
    t_era = tdd(era, "t2m_c", window).rename(columns={"tdd_t2m_c": "tdd_era5"}).drop(columns="tdd_t2m_c_n")
    df = df.merge(t_station, on="year").merge(t_era, on="year")
    df["tdd_days_filled"] = df["year"].map(filled_days).fillna(0).astype(int)

    # Exploratory covariates.
    e = _doy(era)
    df["max_snow_depth_cm"] = df["year"].map(e[e["doy"] <= 151].groupby("year")["snow_depth_cm"].max())
    p = _doy(st)
    lo, hi = dcfg["spring_precip_doy"]
    df["spring_precip_mm"] = df["year"].map(p[(p["doy"] >= lo) & (p["doy"] <= hi)].groupby("year")["precip_mm"].sum(min_count=40))

    config.ensure_dirs()
    df.to_csv(config.PROCESSED / "drivers.csv", index=False)
    return df


def load() -> pd.DataFrame:
    return pd.read_csv(config.PROCESSED / "drivers.csv")
