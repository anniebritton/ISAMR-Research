"""Environment and Climate Change Canada daily records for Churchill, Manitoba.

The Churchill record is split across several climate IDs.
Each variable is spliced from the IDs listed in config.yaml, in priority order, over their date ranges.
"""

from __future__ import annotations

import pandas as pd
import requests

from . import config

FIELDS = ["LOCAL_DATE", "MEAN_TEMPERATURE", "TOTAL_PRECIPITATION", "SNOW_ON_GROUND"]


def fetch(climate_id: str, start: str, end: str) -> pd.DataFrame:
    cfg = config.load()
    params = {
        "f": "json",
        "limit": 10000,
        "CLIMATE_IDENTIFIER": climate_id,
        "datetime": f"{start}/{end}",
        "properties": ",".join(FIELDS),
        "sortby": "LOCAL_DATE",
    }
    r = requests.get(cfg["station"]["api"], params=params, timeout=120)
    r.raise_for_status()
    df = pd.DataFrame([f["properties"] for f in r.json()["features"]])
    df["date"] = pd.to_datetime(df["LOCAL_DATE"]).dt.normalize()
    df["climate_id"] = climate_id
    return df.drop(columns="LOCAL_DATE")


def _splice(series_cfg: list[dict], column: str) -> pd.DataFrame:
    parts = []
    for i, s in enumerate(series_cfg):
        df = fetch(s["climate_id"], s["start"], s["end"])
        parts.append(df[["date", column, "climate_id"]].dropna(subset=[column]).assign(priority=i))
    df = pd.concat(parts).sort_values(["date", "priority"]).drop_duplicates("date")
    return df.drop(columns="priority").rename(columns={"climate_id": f"{column.lower()}_source"})


def run() -> pd.DataFrame:
    """Download, splice, and cache the station series to data/raw/station.csv."""
    cfg = config.load()["station"]
    first, last = config.load()["years"]
    days = pd.DataFrame({"date": pd.date_range(f"{first}-01-01", f"{last}-12-31")})
    temp = _splice(cfg["temperature"], "MEAN_TEMPERATURE")
    snow = _splice(cfg["snow_on_ground"], "SNOW_ON_GROUND")
    precip = _splice(cfg["temperature"], "TOTAL_PRECIPITATION")
    out = days.merge(temp, on="date", how="left").merge(snow, on="date", how="left").merge(precip, on="date", how="left")
    out = out.rename(columns={
        "MEAN_TEMPERATURE": "tmean_c", "SNOW_ON_GROUND": "snow_on_ground_cm", "TOTAL_PRECIPITATION": "precip_mm",
    })
    config.ensure_dirs()
    out.to_csv(config.RAW / "station.csv", index=False)
    return out


def load() -> pd.DataFrame:
    path = config.RAW / "station.csv"
    if not path.exists():
        raise FileNotFoundError("No cached station data; run `wapusk extract` first.")
    return pd.read_csv(path, parse_dates=["date"])


AHCCD_API = "https://api.weather.gc.ca/collections/ahccd-monthly/items"


def ahccd_spring(climate_id: str = "5060608", months: tuple[str, ...] = ("Apr", "May")) -> pd.DataFrame:
    """Homogenized (AHCCD Gen3) monthly mean temperature at Churchill, averaged over spring months.

    Vincent et al. (2020) homogenized series; used only as a sensitivity check on the spliced raw station record.
    """
    path = config.RAW / "ahccd_monthly.csv"
    if path.exists():
        df = pd.read_csv(path)
    else:
        r = requests.get(AHCCD_API, params={"f": "json", "limit": 5000, "station_id__id_station": climate_id}, timeout=120)
        r.raise_for_status()
        df = pd.DataFrame([f["properties"] for f in r.json()["features"]])
        df = df[["date", "period_value__valeur_periode", "temp_mean__temp_moyenne"]].rename(
            columns={"period_value__valeur_periode": "month", "temp_mean__temp_moyenne": "tmean_c"})
        config.ensure_dirs()
        df.to_csv(path, index=False)
    df["year"] = df["date"].str[:4].astype(int)
    df = df[df["tmean_c"] > -9999]  # AHCCD missing-value code is -9999.9
    spring = df[df["month"].isin(months)].groupby("year")["tmean_c"].agg(["mean", "count"])
    spring = spring[spring["count"] == len(months)]
    return spring["mean"].rename("ahccd_spring_tmean_c").reset_index()
