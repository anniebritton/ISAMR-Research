# Wapusk Green-Up

A case study of what coding agents contributed to a complete remote sensing analysis, as builder, optimizer, and auditor,
using spring green-up in Wapusk National Park, Manitoba, 2001–2024, as the worked example.
Written for the [International Student-led Arctic Monitoring and Research (ISAMR) Project](https://www.isamr.net/home).

* **Interactive brief:** [anniebritton.github.io/ISAMR-Research](https://anniebritton.github.io/ISAMR-Research/)
* **Report:** [rendered](https://anniebritton.github.io/ISAMR-Research/report.html) · [source](report/report.qmd) (APA citations via `report/apa.csl`)
* **Pre-registration:** [`prereg.md`](prereg.md)

## Research Questions

* **RQ1:** what did agents contribute in each role (builder, optimizer, auditor)?
* **RQ2:** did the optimizer's improvements carry over to the scientific result?
* **RQ3:** how did the optimizer behave under a fixed objective?
* **Worked example (pre-registered):** has spring mid-green-up shifted since 2001 (H1),
  and is it associated with snow-off (H2) and spring warmth beyond snow-off (H3)?

## Findings

* **Auditors caught most of the consequential problems.**
  Of 24 recorded, the plan reviewer, literature auditors, and referee caught 20, including an optimisation objective that would have biased the trend
  and a misreported variance partition ([`agent_contributions.csv`](results/tables/agent_contributions.csv)).
* **The optimizer's gains did not transfer.**
  Held-out synthetic error fell from 4.65 to 4.39 days, but year-to-year agreement with MCD12Q2 on real pixels fell from 0.900 to 0.881;
  the best version for the science was iteration 8, not the last.
* **The optimizer learned the benchmark.**
  26 of its 33 rationales reasoned from the readable benchmark generator, it kept 4 of 24 substantive changes,
  and it gamed a line-count penalty once its ideas ran out ([`LESSONS.md`](autoresearch/LESSONS.md)).
* **Worked example.**
  No detectable trend in mid-green-up (+0.03 days/yr, 95% CI −0.33 to +0.47); snow-off and April–May warmth explain 77% of year-to-year variation.

![Annual mid-green-up, 2001–2024](results/figures/greenup_series.png)

## Using These Findings

* **Park managers and ecologists:** snow-off and April–May warmth, both known by the end of May in 20 of 24 years,
  predicted mid-green-up to within about four days; there is no detectable long-term trend, but moderate advances cannot be excluded.
* **Applying the method to another park:** replace the boundary GeoJSON, station climate IDs, and seasonal windows in
  [`config.yaml`](config.yaml), then run `uv run wapusk sample` and `uv run wapusk all`.
  Outside Canada, use ERA5-Land degree days (`tdd_era5`) in place of the station series.
* **Building agent loops:** reuse [`autoresearch/`](autoresearch/) for any method that fits in one function with a measurable error;
  the five design rules are in the report's Applications section and [`autoresearch/LESSONS.md`](autoresearch/LESSONS.md).

## Repository Layout

* [`config.yaml`](config.yaml): datasets, masks, windows, and the pre-registered primary specification
* [`src/wapusk_greenup/`](src/wapusk_greenup/): the pipeline
  - `extract.py`, `station.py`: Earth Engine and ECCC downloads into `data/raw/`
  - `smoothers.py`: pre-registered green-up extractors
  - `phenology.py`, `drivers.py`: per-pixel green-up and annual predictors
  - `stats.py`, `analysis.py`: trend, power, driver models, and robustness grid
  - `revision.py`: post-hoc checks requested by the referee report
  - `plots.py`, `site.py`, `cli.py`: figures, data for the interactive brief, and the `wapusk` command
  - `method.py`: the autoresearch agent's candidate extractor, never used in the confirmatory analysis
* [`autoresearch/`](autoresearch/): the sandboxed agent loop, its ledger, evaluation, ablation, and [lessons](autoresearch/LESSONS.md)
* [`data/`](data/): park boundary, the fixed pixel sample, and derived tables; raw extracts are gitignored
* [`results/`](results/): figures, result tables, and the [AI referee report](results/review.md)
* [`report/`](report/): the report and its bibliography
* [`site/`](site/): the interactive brief, deployed to GitHub Pages
* [`docs/`](docs/): [methods justification](docs/methods_justification.md) and [future work](docs/future_work.md)
* [`notebooks/`](notebooks/): the original 2023 exploration (archived) and an exploratory appendix
* [`DATA.md`](DATA.md): every dataset with its version, licence, and citation

## Setup

Requires Python 3.11+, [uv](https://docs.astral.sh/uv/), and an Earth Engine account registered to a Google Cloud project.

```sh
uv sync
uv run earthengine authenticate
```

Set `gee_project` in [`config.yaml`](config.yaml) to your Cloud project ID.

## Running

```sh
uv run wapusk extract                # Earth Engine + station data into data/raw/ (cached)
uv run wapusk phenology              # green-up for every pixel-year and specification
uv run wapusk drivers                # annual predictors
uv run wapusk confirmatory           # pre-registered analysis; runs once and needs a committed prereg.md
uv run wapusk sensitivity            # MCD12Q2, NBAR, stratum, and predictor checks
uv run wapusk multiverse             # 24-specification robustness grid
uv run wapusk parameter-sensitivity  # post-hoc one-at-a-time parameter tests
uv run wapusk stat-robustness        # post-hoc statistical checks
uv run wapusk revision-checks        # post-hoc checks prompted by the referee report
uv run wapusk figures                # report figures
uv run wapusk site                   # data for the interactive brief
```

`uv run wapusk all` runs every step after sampling.
`wapusk sample` redraws the pixel sample, which is committed and should not change.
The view-angle sensitivity test needs one extra pull: `uv run wapusk extract --source mod09ga_zenith`.

To preview the brief locally, run `uv run wapusk site`, then `python -m http.server -d site` and open `localhost:8000`.
The report renders with [Quarto](https://quarto.org) (`quarto render report/report.qmd`); the Pages workflow renders it automatically.

The autoresearch loop has its own instructions in [`autoresearch/README.md`](autoresearch/README.md).

## Tests

```sh
uv run pytest            # unit tests on synthetic data
uv run pytest -m gee     # integration tests against the real Earth Engine backend
```

## Status

The confirmatory analysis, robustness checks, and referee revisions are complete.
Open items are tracked in [`docs/future_work.md`](docs/future_work.md),
including a clean-clone reproducibility run, a Zenodo archive of the raw extracts, ground phenology for validation, and a second agent loop.

## Use of AI

The pipeline, pre-registration, and first draft of the report were produced by an AI coding agent (Claude Code) under the author's direction,
and an AI referee reviewed the draft.
The author is responsible for the research questions, design decisions, and conclusions.

## Citation

See [`CITATION.cff`](CITATION.cff).

## Licence

Code is MIT-licensed; see [`LICENSE`](LICENSE).
Data sources keep their own licences; see [`DATA.md`](DATA.md).
