# Future Work

Open items, in rough priority order.

## Completing the Current Study

* **Author review.**
  The pipeline, pre-registration, and drafts were produced by an AI coding agent.
  The design choices to check first are ERA5-Land as the snow-off source, the April–May TDD window, and the 10% water screen.
* **Clean-clone reproducibility run.**
  Run `uv run wapusk all` from a fresh clone with Earth Engine credentials,
  and compare `data/processed/pixel_greenup.csv.gz` with the committed copy within a tolerance.
* **Archive raw extracts.**
  Deposit `data/raw/` (about 21 MB) on Zenodo with a DOI, and link it from `DATA.md`.
* **Second referee pass** on the revised report.

## Strengthening the Findings

* **Ground truth.**
  Field phenology from Churchill Northern Studies Centre, the long-term goose research at La Pérouse Bay,
  or any PhenoCam near Churchill would turn the MCD12Q2 consistency check into validation.
* **Longer and finer record.**
  Landsat and Sentinel-2 (HLS, 30 m) would improve trend sensitivity and cover the wet margins the 500 m sample excludes.
* **Temperature window.**
  Pre-register a principled alternative, such as degree days anchored at snow-off, and test it.
* **Spatial pattern.**
  Map per-pixel trends and driver effects to test coast-to-inland and wetland-to-upland differences.
* **Terra orbit drift.**
  Compare Terra (MOD09GA) and Aqua (MYD09GA) for 2022–2024.
* **Whittaker λ.**
  Select λ per pixel with the V-curve (Frasso & Eilers 2015) instead of a fixed value.

## Agent Loop, Version 2

See [`autoresearch/LESSONS.md`](../autoresearch/LESSONS.md) for the reasoning behind each item.

* Score the downstream statistic: synthetic multi-year panels with a known trend and driver effect.
* Keep a Pareto archive across held-out error, interannual fidelity, and failure rate; select once at freeze.
* Reject changes whose outputs are identical to the incumbent's, instead of rewarding line count.
* Build visible seasons from real pixel-years.
* Give the agent a sandboxed visible-set evaluation tool and measure whether the held-out gap widens.
* Stop after three consecutive no-edit iterations.
* Compare several models, or several independent agents, on the same loop.

## Ideas From the Original Notebook

* Hudson Bay sea ice as a coastal driver; note that Assmann et al. (2019) found regional sea ice did not explain tundra phenology.
* Albedo (MCD43A3) to link snow and surface energy balance to melt timing.
* [Prairie Climate Centre](https://prairieclimatecentre.ca/about-us/) projections of green-up under future climate.
* Predicting caribou arrival from climate and phenology, which needs caribou observation or collar data.
