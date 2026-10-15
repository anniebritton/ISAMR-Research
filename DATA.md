# Data Sources

Every dataset used, with its identifier, version, licence, and citation.
Image counts and first/last image IDs per year are in [`data/processed/extraction_manifest.json`](data/processed/extraction_manifest.json).

## Boundary and Land Cover

* **Wapusk National Park boundary**
  - Source: Natural Resources Canada, Canada Lands Survey System, `Administrative_Area` layer of
    [`WAPUSK_NATIONAL_PARK_OF_CANADA_SHP.zip`](https://clss.nrcan-rncan.gc.ca/data-donnees/sgb_datasets/mb/WAPUSK_NATIONAL_PARK_OF_CANADA/)
  - Licence: [Open Government Licence – Canada](https://open.canada.ca/en/open-government-licence-canada)
  - Stored as [`data/aoi/wapusk.geojson`](data/aoi/wapusk.geojson), reprojected from NAD83(CSRS) / UTM 15N to WGS 84; retrieved 2026-10-14
* **ESA WorldCover 10 m v200** (`ESA/WorldCover/v200`)
  - Licence: CC BY 4.0
  - Citation: Zanaga, D., et al. (2022). ESA WorldCover 10 m 2021 v200. https://doi.org/10.5281/zenodo.7254221
  - Accuracy: [Product Validation Report v2.0](https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/docs/WorldCover_PVR_V2.0.pdf);
    herbaceous wetland user's accuracy is 23–31%, so the strata are a sampling design rather than validated classes
* **JRC Global Surface Water v1.4** (`JRC/GSW1_4/GlobalSurfaceWater`)
  - Licence: CC BY 4.0
  - Citation: Pekel, J.-F., Cottam, A., Gorelick, N., & Belward, A. S. (2016). High-resolution mapping of global surface water
    and its long-term changes. *Nature*, 540, 418–422.

## MODIS (NASA LP DAAC and NSIDC, accessed through Google Earth Engine)

NASA data carry no restrictions on reuse; cite each product.

* **MOD09GA v061** (`MODIS/061/MOD09GA`): daily surface reflectance, primary NDVI source
  (cached as `mod09ga`, plus `mod09ga_zenith` with sensor zenith for the view-angle sensitivity test)
  - Vermote, E., & Wolfe, R. (2021). MODIS/Terra Surface Reflectance Daily L2G Global 1km and 500m SIN Grid V061.
    NASA EOSDIS LP DAAC. https://doi.org/10.5067/MODIS/MOD09GA.061
* **MCD43A4 v061 and MCD43A2 v061** (`MODIS/061/MCD43A4`, `MODIS/061/MCD43A2`): NBAR NDVI sensitivity series
  - Schaaf, C., & Wang, Z. (2021). MODIS/Terra+Aqua BRDF/Albedo Nadir BRDF Adjusted Ref Daily L3 Global 500m V061.
    NASA EOSDIS LP DAAC. https://doi.org/10.5067/MODIS/MCD43A4.061
* **MOD10A1 v061** (`MODIS/061/MOD10A1`): snow-off cross-check
  - Hall, D. K., & Riggs, G. A. (2021). MODIS/Terra Snow Cover Daily L3 Global 500m SIN Grid, Version 61. NSIDC DAAC.
    https://doi.org/10.5067/MODIS/MOD10A1.061
* **MCD12Q2 v061** (`MODIS/061/MCD12Q2`): validation only
  - Friedl, M., Gray, J., & Sulla-Menashe, D. (2022). MODIS/Terra+Aqua Land Cover Dynamics Yearly L3 Global 500m SIN Grid V061.
    NASA EOSDIS LP DAAC. https://doi.org/10.5067/MODIS/MCD12Q2.061

## Reanalysis

* **ERA5-Land daily aggregates** (`ECMWF/ERA5_LAND/DAILY_AGGR`): primary snow-off, TDD sensitivity, snow depth
  - Licence: Copernicus licence; attribution required:
    "Contains modified Copernicus Climate Change Service information 2026."
  - Citation: Muñoz-Sabater, J., et al. (2021). ERA5-Land: a state-of-the-art global reanalysis dataset for land applications.
    *Earth System Science Data*, 13, 4349–4383. https://doi.org/10.5194/essd-13-4349-2021

## Station

* **Environment and Climate Change Canada daily climate data, Churchill, Manitoba**
  - Accessed through the [MSC GeoMet OGC API](https://api.weather.gc.ca/collections/climate-daily)
  - Climate IDs 5060600 (CHURCHILL A, 2001–2005), 5060608 (CHURCHILL CLIMATE, 2006–2024), 5060595 (CHURCHILL A, gap fill)
  - Licence: [Open Government Licence – Canada](https://open.canada.ca/en/open-government-licence-canada)

* **AHCCD Gen3 homogenized monthly temperature, Churchill (5060608)**
  - Accessed through the [MSC GeoMet `ahccd-monthly` collection](https://api.weather.gc.ca/collections/ahccd-monthly); used only to check the spliced station record
  - Licence: [Open Government Licence – Canada](https://open.canada.ca/en/open-government-licence-canada)
  - Citation: Vincent, L. A., Hartwell, M. M., & Wang, X. L. (2020). A third generation of homogenized temperature for trend analysis
    and monitoring changes in Canada's climate. *Atmosphere-Ocean*, 58(3), 173–191. https://doi.org/10.1080/07055900.2020.1765728

## Earth Engine

Gorelick, N., Hancher, M., Dixon, M., Ilyushchenko, S., Thau, D., & Moore, R. (2017).
Google Earth Engine: Planetary-scale geospatial analysis for everyone. *Remote Sensing of Environment*, 202, 18–27.

## Archive

The raw extracts in `data/raw/` (about 21 MB) are gitignored and not yet archived; a Zenodo deposit is listed in [`docs/future_work.md`](docs/future_work.md).

## Reproducing the Extraction

Earth Engine collections are reprocessed occasionally, so a fresh extraction may differ slightly from the cached run.
Compare a re-extracted year against [`data/processed/extraction_manifest.json`](data/processed/extraction_manifest.json)
and the committed `pixel_greenup.csv.gz` within a tolerance, not byte for byte.
