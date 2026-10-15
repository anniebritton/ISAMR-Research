"""Earth Engine helpers: initialisation, MODIS QA masking, NDVI.

Ported from the original notebook (cells 10, 11, 14) with these changes:
collection 061 instead of the deprecated 006, a full state_1km and QC_500m mask instead of bit 10 alone,
and snow kept as a separate flag so snow-covered days can anchor the dormant baseline.
"""

from __future__ import annotations

import ee

from . import config

# MOD09GA state_1km bit layout (MOD09 user guide, collection 6.1).
CLOUD_STATE = (0, 2)        # 00 clear, 01 cloudy, 10 mixed, 11 not set (assumed clear)
CLOUD_SHADOW = 2
CIRRUS = (8, 2)             # 00 none, 01 small, 10 average, 11 high
INTERNAL_CLOUD = 10
MOD35_SNOW = 12
ADJACENT_CLOUD = 13
INTERNAL_SNOW = 15


def initialize() -> None:
    cfg = config.load()
    try:
        ee.Initialize(project=cfg["gee_project"])
    except Exception:
        ee.Authenticate()
        ee.Initialize(project=cfg["gee_project"])


def _bit(img: ee.Image, bit: int) -> ee.Image:
    return img.rightShift(bit).bitwiseAnd(1)


def _bits(img: ee.Image, start: int, width: int) -> ee.Image:
    return img.rightShift(start).bitwiseAnd((1 << width) - 1)


def snow_flag(image: ee.Image) -> ee.Image:
    """1 where either MODIS snow flag (internal or MOD35) is set."""
    state = image.select("state_1km")
    return _bit(state, INTERNAL_SNOW).Or(_bit(state, MOD35_SNOW)).rename("snow")


def clear_mask(image: ee.Image, level: str, skip_zenith: bool = False) -> ee.Image:
    """Boolean image of snow-free, cloud-free pixels at the requested strictness."""
    opts = dict(config.load()["masks"][level])
    if skip_zenith:
        opts.pop("max_sensor_zenith_deg", None)
    state = image.select("state_1km")
    cloud_state = _bits(state, *CLOUD_STATE)
    ok = cloud_state.eq(0).Or(cloud_state.eq(3))
    if opts.get("internal_cloud"):
        ok = ok.And(_bit(state, INTERNAL_CLOUD).eq(0))
    if opts.get("internal_snow"):
        ok = ok.And(_bit(state, INTERNAL_SNOW).eq(0))
    if opts.get("cloud_shadow"):
        ok = ok.And(_bit(state, CLOUD_SHADOW).eq(0))
    if opts.get("mod35_snow"):
        ok = ok.And(_bit(state, MOD35_SNOW).eq(0))
    if opts.get("adjacent_cloud"):
        ok = ok.And(_bit(state, ADJACENT_CLOUD).eq(0))
    if "max_cirrus" in opts:
        ok = ok.And(_bits(state, *CIRRUS).lte(opts["max_cirrus"]))
    if "max_sensor_zenith_deg" in opts:
        ok = ok.And(image.select("SensorZenith").lt(opts["max_sensor_zenith_deg"] * 100))
    # QC_500m bits 0-1: MODLAND QA, 00 ideal quality, 01 less than ideal.
    ok = ok.And(_bits(image.select("QC_500m"), 0, 2).lte(1))
    return ok


def daily_ndvi(image: ee.Image) -> ee.Image:
    """NDVI under both mask levels plus the snow flag for one MOD09GA day."""
    ndvi = image.normalizedDifference(["sur_refl_b02", "sur_refl_b01"])
    return (
        ndvi.updateMask(clear_mask(image, "strict")).rename("ndvi_strict")
        .addBands(ndvi.updateMask(clear_mask(image, "lenient")).rename("ndvi_lenient"))
        .addBands(snow_flag(image))
        .copyProperties(image, ["system:time_start"])
    )


def daily_ndvi_zenith(image: ee.Image) -> ee.Image:
    """Strict-mask NDVI without the view-angle filter, plus sensor zenith (degrees), for the zenith sensitivity check."""
    ndvi = image.normalizedDifference(["sur_refl_b02", "sur_refl_b01"])
    return (
        ndvi.updateMask(clear_mask(image, "strict", skip_zenith=True)).rename("ndvi_strict_anyzenith")
        .addBands(image.select("SensorZenith").multiply(0.01).rename("sensor_zenith"))
        .addBands(snow_flag(image))
        .copyProperties(image, ["system:time_start"])
    )


def daily_nbar_ndvi(nbar: ee.Image) -> ee.Image:
    """NDVI from MCD43A4 NBAR, full BRDF inversions only, with the MCD43A2 snow flag."""
    q1 = nbar.select("BRDF_Albedo_Band_Mandatory_Quality_Band1").eq(0)
    q2 = nbar.select("BRDF_Albedo_Band_Mandatory_Quality_Band2").eq(0)
    ndvi = nbar.normalizedDifference(["Nadir_Reflectance_Band2", "Nadir_Reflectance_Band1"])
    snow = ee.Image(nbar.get("quality")).select("Snow_BRDF_Albedo").rename("snow")
    return (
        ndvi.updateMask(q1.And(q2).And(snow.eq(0))).rename("ndvi_nbar")
        .addBands(snow)
        .copyProperties(nbar, ["system:time_start"])
    )


def modis_projection() -> ee.Projection:
    cfg = config.load()
    return ee.ImageCollection(cfg["datasets"]["surface_reflectance"]).first().select("sur_refl_b01").projection()


# Native MOD09GA 500 m grid. Sampling on this grid returns each pixel centre unresampled.
MODIS_CRS = "SR-ORG:6974"
MODIS_TRANSFORM = [463.3127165279165, 0, -20015109.354, 0, -463.3127165279167, 10007554.677003]


def grid_args() -> dict:
    return {"crs": MODIS_CRS, "crsTransform": MODIS_TRANSFORM}
