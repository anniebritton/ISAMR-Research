"""Pull every Earth Engine input into cached files under data/raw/.

Each source is fetched one year at a time, which keeps every request under the getRegion and getInfo limits.
Reruns skip years whose file already exists unless force=True.
A manifest records the collection, image count, and first/last image ID per year,
so a later re-extraction can be compared against the cached run.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import ee
import numpy as np
import pandas as pd

from . import aoi, config, gee

MANIFEST = config.RAW / "manifest.json"


def _date_range(year: int) -> tuple[str, str]:
    first, last = config.load()["extract_doy"]
    start = pd.Timestamp(year, 1, 1) + pd.Timedelta(days=first - 1)
    end = pd.Timestamp(year, 1, 1) + pd.Timedelta(days=last)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def _multipoint() -> ee.Geometry:
    return ee.Geometry.MultiPoint([p["geometry"]["coordinates"] for p in aoi.load_points()])


def _region_to_frame(rows: list[list], bands: list[str]) -> pd.DataFrame:
    """Convert getRegion output to a tidy frame keyed by pixel_id and date."""
    header, *data = rows
    df = pd.DataFrame(data, columns=header)
    df["date"] = pd.to_datetime(df["time"], unit="ms").dt.normalize()
    # getRegion on the native grid reports pixel centres; match rows to sample points by grid cell.
    cells = aoi.grid_cells(df["longitude"].to_numpy(float), df["latitude"].to_numpy(float))
    lookup = {(p["properties"]["col"], p["properties"]["row"]): p["properties"]["pixel_id"] for p in aoi.load_points()}
    df["pixel_id"] = [lookup[c] for c in cells]
    return df[["pixel_id", "date", *bands]].sort_values(["pixel_id", "date"]).reset_index(drop=True)


def _record(source: str, year: int, coll: ee.ImageCollection) -> dict:
    ids = coll.aggregate_array("system:index").getInfo()
    return {
        "source": source,
        "year": year,
        "n_images": len(ids),
        "first_id": ids[0] if ids else None,
        "last_id": ids[-1] if ids else None,
        "extracted_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def mod09ga_year(year: int) -> tuple[pd.DataFrame, dict]:
    cfg = config.load()
    start, end = _date_range(year)
    coll = ee.ImageCollection(cfg["datasets"]["surface_reflectance"]).filterDate(start, end)
    bands = ["ndvi_strict", "ndvi_lenient", "snow"]
    rows = coll.map(gee.daily_ndvi).getRegion(_multipoint(), **gee.grid_args()).getInfo()
    return _region_to_frame(rows, bands), _record("mod09ga", year, coll)


def mod09ga_zenith_year(year: int) -> tuple[pd.DataFrame, dict]:
    cfg = config.load()
    start, end = _date_range(year)
    coll = ee.ImageCollection(cfg["datasets"]["surface_reflectance"]).filterDate(start, end)
    rows = coll.map(gee.daily_ndvi_zenith).getRegion(_multipoint(), **gee.grid_args()).getInfo()
    df = _region_to_frame(rows, ["ndvi_strict_anyzenith", "sensor_zenith", "snow"])
    return df, _record("mod09ga_zenith", year, coll)


def nbar_year(year: int) -> tuple[pd.DataFrame, dict]:
    cfg = config.load()
    start, end = _date_range(year)
    nbar = ee.ImageCollection(cfg["datasets"]["nbar"]).filterDate(start, end)
    qa = ee.ImageCollection(cfg["datasets"]["nbar_quality"]).filterDate(start, end)
    joined = ee.ImageCollection(
        ee.Join.saveFirst("quality").apply(nbar, qa, ee.Filter.equals(leftField="system:index", rightField="system:index"))
    )
    rows = joined.map(gee.daily_nbar_ndvi).getRegion(_multipoint(), **gee.grid_args()).getInfo()
    return _region_to_frame(rows, ["ndvi_nbar", "snow"]), _record("nbar", year, nbar)


def era5_year(year: int) -> tuple[pd.DataFrame, dict]:
    """Daily park-mean ERA5-Land temperature, snow, and precipitation."""
    cfg = config.load()
    coll = ee.ImageCollection(cfg["datasets"]["reanalysis"]).filterDate(f"{year}-01-01", f"{year + 1}-01-01")
    bands = ["temperature_2m", "snow_cover", "snow_depth", "total_precipitation_sum"]
    geom = aoi.boundary()

    def reduce(img: ee.Image) -> ee.Feature:
        stats = img.select(bands).reduceRegion(ee.Reducer.mean(), geom, scale=11132, maxPixels=1e9)
        return ee.Feature(None, stats).set("date", img.date().format("YYYY-MM-dd"))

    feats = coll.map(reduce).getInfo()["features"]
    df = pd.DataFrame([f["properties"] for f in feats])
    df["date"] = pd.to_datetime(df["date"])
    df["temperature_2m"] = df["temperature_2m"] - 273.15
    df["snow_depth"] = df["snow_depth"] * 100          # m -> cm
    df["total_precipitation_sum"] = df["total_precipitation_sum"] * 1000  # m -> mm
    df = df.rename(columns={
        "temperature_2m": "t2m_c", "snow_depth": "snow_depth_cm", "total_precipitation_sum": "precip_mm",
    })
    return df[["date", "t2m_c", "snow_cover", "snow_depth_cm", "precip_mm"]], _record("era5", year, coll)


def mod10a1_year(year: int) -> tuple[pd.DataFrame, dict]:
    """Daily park-mean MODIS NDSI snow cover (NDSI x 100) and the fraction of valid pixels."""
    cfg = config.load()
    start, end = _date_range(year)
    coll = ee.ImageCollection(cfg["datasets"]["snow"]).filterDate(start, end)
    geom = aoi.boundary()

    def reduce(img: ee.Image) -> ee.Feature:
        ndsi = img.select("NDSI_Snow_Cover")
        good = img.select("NDSI_Snow_Cover_Basic_QA").lte(2)
        # Unmask so that cloud, night, and fill pixels count as invalid in the fraction.
        valid = ndsi.lte(100).And(good).unmask(0)
        stats = (
            ndsi.updateMask(valid).rename("ndsi").addBands(valid.rename("valid_fraction"))
            .reduceRegion(ee.Reducer.mean(), geom, scale=500, maxPixels=1e9, tileScale=4)
        )
        return ee.Feature(None, stats).set("date", img.date().format("YYYY-MM-dd"))

    feats = coll.map(reduce).getInfo()["features"]
    df = pd.DataFrame([f["properties"] for f in feats])
    df["date"] = pd.to_datetime(df["date"])
    return df[["date", "ndsi", "valid_fraction"]], _record("mod10a1", year, coll)


def mcd12q2_all() -> tuple[pd.DataFrame, dict]:
    """MCD12Q2 cycle-1 green-up metrics at every sample pixel for all years."""
    cfg = config.load()
    first, last = cfg["years"]
    coll = ee.ImageCollection(cfg["datasets"]["phenology_product"]).filterDate(f"{first}-01-01", f"{last + 1}-01-01")
    bands = ["NumCycles", "Greenup_1", "MidGreenup_1", "QA_Detailed_1"]
    rows = coll.select(bands).getRegion(_multipoint(), **gee.grid_args()).getInfo()
    df = _region_to_frame(rows, bands)
    df["year"] = df["date"].dt.year
    # QA_Detailed bits 2-3 hold MidGreenup quality: 0 best, 1 good, 2 fill, 3 low.
    df["mid_qa"] = np.right_shift(df["QA_Detailed_1"].fillna(8).astype(int).to_numpy(), 2) & 3
    for col in ("Greenup_1", "MidGreenup_1"):
        dates = pd.to_datetime(df[col], unit="D", origin="1970-01-01")
        df[col.replace("_1", "_doy")] = np.where(dates.dt.year == df["year"], dates.dt.dayofyear, np.nan)
    rec = {"source": "mcd12q2", "year": "all", "n_images": int(coll.size().getInfo())}
    return df[["pixel_id", "year", "NumCycles", "Greenup_doy", "MidGreenup_doy", "mid_qa"]], rec


YEARLY = {"mod09ga": mod09ga_year, "nbar": nbar_year, "era5": era5_year, "mod10a1": mod10a1_year,
          "mod09ga_zenith": mod09ga_zenith_year}


def _path(source: str, year: int | None = None) -> Path:
    return config.RAW / source / (f"{year}.csv.gz" if year is not None else "all.csv.gz")


def _update_manifest(records: list[dict]) -> None:
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    for r in records:
        manifest[f"{r['source']}/{r['year']}"] = r
    MANIFEST.write_text(json.dumps(dict(sorted(manifest.items())), indent=1))


def run(sources: list[str] | None = None, years: list[int] | None = None, force: bool = False, workers: int = 4) -> None:
    config.ensure_dirs()
    gee.initialize()
    cfg = config.load()
    years = years or cfg["year_list"]
    # The zenith sensitivity source is pulled only on request.
    sources = sources or [*[k for k in YEARLY if k != "mod09ga_zenith"], "mcd12q2"]
    jobs = []
    for source in sources:
        if source == "mcd12q2":
            if force or not _path(source).exists():
                jobs.append((source, None))
            continue
        for y in years:
            if force or not _path(source, y).exists():
                jobs.append((source, y))

    def do(job: tuple[str, int | None]) -> dict:
        source, year = job
        df, rec = mcd12q2_all() if year is None else YEARLY[source](year)
        path = _path(source, year)
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False)
        print(f"{source} {year or 'all'}: {len(df)} rows", flush=True)
        return rec

    def attempt(job: tuple[str, int | None]) -> dict | None:
        try:
            return do(job)
        except Exception as e:  # keep going; report failures at the end
            print(f"FAILED {job}: {e}", flush=True)
            return None

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(attempt, jobs))
    _update_manifest([r for r in results if r])
    failed = [j for j, r in zip(jobs, results) if r is None]
    if failed:
        raise RuntimeError(f"{len(failed)} extraction jobs failed: {failed}")


def load(source: str) -> pd.DataFrame:
    """Concatenate cached files for a source."""
    if source == "mcd12q2":
        return pd.read_csv(_path(source))
    files = sorted((config.RAW / source).glob("*.csv.gz"))
    if not files:
        raise FileNotFoundError(f"No cached {source} files; run `wapusk extract` first.")
    return pd.concat([pd.read_csv(f, parse_dates=["date"]) for f in files], ignore_index=True)
