"""Park boundary, land masks, and the fixed pixel sample used for per-pixel phenology."""

from __future__ import annotations

import json

import ee

from . import config, gee


def boundary_geojson() -> dict:
    cfg = config.load()
    with open(config.ROOT / cfg["aoi"]["boundary"]) as f:
        return json.load(f)


def boundary() -> ee.Geometry:
    return ee.Geometry(boundary_geojson()["features"][0]["geometry"])


# MODIS sinusoidal grid (SR-ORG:6974).
SINUSOIDAL = "+proj=sinu +lon_0=0 +x_0=0 +y_0=0 +R=6371007.181 +units=m +no_defs"
GRID_ORIGIN = (-20015109.354, 10007554.677)
PIXEL_SIZE = 463.312716528


def grid_centres() -> list[tuple[float, float]]:
    """Sinusoidal x/y of every MODIS 500 m pixel centre inside the park boundary."""
    import numpy as np
    from matplotlib.path import Path
    from pyproj import Transformer

    to_sin = Transformer.from_crs("EPSG:4326", SINUSOIDAL, always_xy=True)
    ring = boundary_geojson()["features"][0]["geometry"]["coordinates"][0]
    xs, ys = to_sin.transform([c[0] for c in ring], [c[1] for c in ring])
    poly = Path(np.column_stack([xs, ys]))
    x0, y0 = GRID_ORIGIN
    col = np.arange(np.floor((min(xs) - x0) / PIXEL_SIZE), np.ceil((max(xs) - x0) / PIXEL_SIZE))
    row = np.arange(np.floor((y0 - max(ys)) / PIXEL_SIZE), np.ceil((y0 - min(ys)) / PIXEL_SIZE))
    cx = x0 + (col + 0.5) * PIXEL_SIZE
    cy = y0 - (row + 0.5) * PIXEL_SIZE
    gx, gy = np.meshgrid(cx, cy)
    pts = np.column_stack([gx.ravel(), gy.ravel()])
    return [tuple(p) for p in pts[poly.contains_points(pts)]]


def grid_cells(lon, lat) -> list[tuple[int, int]]:
    """MODIS grid (col, row) containing each lon/lat."""
    import numpy as np
    from pyproj import Transformer

    x, y = Transformer.from_crs("EPSG:4326", SINUSOIDAL, always_xy=True).transform(lon, lat)
    x0, y0 = GRID_ORIGIN
    col = np.floor((np.asarray(x) - x0) / PIXEL_SIZE).astype(int)
    row = np.floor((y0 - np.asarray(y)) / PIXEL_SIZE).astype(int)
    return list(zip(col.tolist(), row.tolist()))


def _footprints(centres: list[tuple[float, float]]) -> ee.FeatureCollection:
    # Earth Engine cannot parse proj4 strings, so take the unscaled WKT from a MODIS image.
    proj = ee.Projection(gee.modis_projection().wkt())
    half = PIXEL_SIZE / 2
    return ee.FeatureCollection([
        ee.Feature(ee.Geometry.Rectangle([x - half, y - half, x + half, y + half], proj, False), {"cid": i})
        for i, (x, y) in enumerate(centres)
    ])


def _describe(centres: list[tuple[float, float]]) -> list[dict]:
    """Water fraction and modal WorldCover class for each pixel footprint, at native resolution."""
    cfg = config.load()
    occ = ee.Image(cfg["datasets"]["surface_water"]).select("occurrence").unmask(0)
    water = occ.gt(cfg["aoi"]["water_occurrence_threshold"]).rename("water_fraction")
    wc = ee.ImageCollection(cfg["datasets"]["land_cover"]).first().select("Map").rename("landcover")
    fc = _footprints(centres)
    wf = water.reduceRegions(fc, ee.Reducer.mean(), scale=30, tileScale=4).getInfo()["features"]
    lc = wc.reduceRegions(fc, ee.Reducer.mode(), scale=10, tileScale=4).getInfo()["features"]
    by_id = {f["properties"]["cid"]: {"water_fraction": f["properties"].get("mean")} for f in wf}
    for f in lc:
        mode = f["properties"].get("mode")
        # Weighted mode over partial edge pixels returns float noise such as 89.99999999999999.
        by_id[f["properties"]["cid"]]["landcover"] = None if mode is None else int(round(mode))
    return [by_id[i] for i in range(len(centres))]


def _dry_shares(info: list[dict], class_to_stratum: dict, max_wf: float, names: list[str]) -> dict[str, float]:
    dry = [
        class_to_stratum.get(d.get("landcover"))
        for d in info
        if d.get("water_fraction") is not None and d["water_fraction"] <= max_wf
    ]
    counts = {n: dry.count(n) for n in names}
    total = sum(counts.values())
    return {n: round(c / total, 4) for n, c in counts.items()}


def stratum_weights() -> dict[str, float]:
    cfg = config.load()
    with open(config.ROOT / cfg["aoi"]["sample_points"]) as f:
        return json.load(f)["metadata"]["dry_area_share"]


def write_sample_points(n_candidates: int = 6000, batch: int = 500) -> int:
    """Draw the stratified pixel sample once and commit it, so every run uses identical pixels."""
    import numpy as np
    from pyproj import Transformer

    cfg = config.load()
    rng = np.random.default_rng(cfg["aoi"]["sample_seed"])
    centres = grid_centres()
    pick = rng.choice(len(centres), size=min(n_candidates, len(centres)), replace=False)
    cand = [centres[i] for i in pick]
    info: list[dict] = []
    for i in range(0, len(cand), batch):
        info += _describe(cand[i:i + batch])

    class_to_stratum = {c: name for name, classes in cfg["aoi"]["strata"].items() for c in classes}
    per = cfg["aoi"]["points_per_stratum"]
    chosen: dict[str, list[int]] = {name: [] for name in cfg["aoi"]["strata"]}
    for i, d in enumerate(info):
        name = class_to_stratum.get(d.get("landcover"))
        wf = d.get("water_fraction")
        if name and wf is not None and wf <= cfg["aoi"]["max_water_fraction"] and len(chosen[name]) < per:
            chosen[name].append(i)

    to_ll = Transformer.from_crs(SINUSOIDAL, "EPSG:4326", always_xy=True)
    feats = []
    for name, idx in chosen.items():
        for i in idx:
            lon, lat = to_ll.transform(*cand[i])
            feats.append({
                "type": "Feature",
                "properties": {
                    "pixel_id": len(feats),
                    "stratum": name,
                    "landcover": info[i]["landcover"],
                    "water_fraction": round(info[i]["water_fraction"], 4),
                    "col": int((cand[i][0] - GRID_ORIGIN[0]) // PIXEL_SIZE),
                    "row": int((GRID_ORIGIN[1] - cand[i][1]) // PIXEL_SIZE),
                },
                "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]},
            })
    meta = {
        "n_grid_pixels": len(centres),
        "n_candidates": len(cand),
        "candidates_by_stratum": {
            name: sum(class_to_stratum.get(d.get("landcover")) == name for d in info) for name in chosen
        },
        # Share of dry (water fraction within limit) candidates per stratum. Used to area-weight
        # the equal-allocation sample when aggregating to a park-wide value.
        "dry_area_share": _dry_shares(info, class_to_stratum, cfg["aoi"]["max_water_fraction"], list(chosen)),
        "candidates_too_wet": sum((d.get("water_fraction") or 0) > cfg["aoi"]["max_water_fraction"] for d in info),
    }
    with open(config.ROOT / cfg["aoi"]["sample_points"], "w") as f:
        json.dump({"type": "FeatureCollection", "metadata": meta, "features": feats}, f, indent=1)
    return len(feats)


def load_points() -> list[dict]:
    cfg = config.load()
    with open(config.ROOT / cfg["aoi"]["sample_points"]) as f:
        return json.load(f)["features"]


def points_fc() -> ee.FeatureCollection:
    return ee.FeatureCollection([
        ee.Feature(ee.Geometry.Point(p["geometry"]["coordinates"]), {"pixel_id": p["properties"]["pixel_id"]})
        for p in load_points()
    ])
