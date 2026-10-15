"""Command-line entry point: `wapusk <step>`."""

from __future__ import annotations

import json

import typer

app = typer.Typer(no_args_is_help=True, help="Wapusk green-up pipeline.")


@app.command()
def sample() -> None:
    """Draw the stratified pixel sample (once; the result is committed)."""
    from . import aoi, gee

    gee.initialize()
    typer.echo(f"{aoi.write_sample_points()} pixels written")


@app.command()
def extract(force: bool = False, source: list[str] = typer.Option(None), workers: int = 6) -> None:
    """Pull Earth Engine and station data into data/raw/."""
    from . import extract as ex
    from . import station

    ex.run(sources=source or None, force=force, workers=workers)
    station.run()


@app.command()
def phenology() -> None:
    """Fit green-up for every pixel-year and specification."""
    from . import phenology as ph

    ph.run()


@app.command()
def drivers() -> None:
    """Build annual predictors."""
    from . import drivers as dr

    dr.run()


@app.command()
def power() -> None:
    """Minimum detectable trend for prereg.md (uses MCD12Q2, not this study's response)."""
    from . import analysis

    typer.echo(json.dumps(analysis.power_analysis(), indent=2))


@app.command()
def confirmatory(force: bool = typer.Option(False, help="Overwrite an existing confirmatory result.")) -> None:
    """Run the pre-registered analysis. Runs once; requires a committed prereg.md."""
    from . import analysis

    typer.echo(json.dumps(analysis.confirmatory(force=force), indent=2, default=float))


@app.command()
def sensitivity() -> None:
    """MCD12Q2, NBAR, stratum, and predictor cross-checks."""
    from . import analysis

    analysis.sensitivity()


@app.command()
def multiverse() -> None:
    """Run H1-H3 across the 24-specification robustness grid."""
    from . import analysis

    typer.echo(analysis.multiverse().to_string())


@app.command(name="parameter-sensitivity")
def parameter_sensitivity() -> None:
    """Post-hoc one-at-a-time sensitivity to parameters the literature does not fix."""
    from . import analysis

    typer.echo(analysis.parameter_sensitivity().round(3).to_string())


@app.command(name="stat-robustness")
def stat_robustness() -> None:
    """Post-hoc MK variants, own-series MDT, BCa interval, AHCCD and snow-off checks."""
    from . import analysis

    typer.echo(json.dumps(analysis.statistical_robustness(), indent=2, default=float))


@app.command(name="revision-checks")
def revision_checks() -> None:
    """Post-hoc checks requested by the referee report."""
    from . import revision

    typer.echo(json.dumps(revision.run(), indent=2, default=float))


@app.command(name="site")
def build_site() -> None:
    """Write site/data.json for the interactive research brief."""
    from . import site

    d = site.build()
    typer.echo(f"site/data.json: {len(d['seasons'])} example pixel-years")


@app.command()
def figures() -> None:
    """Render report figures to results/figures/."""
    from . import plots

    plots.run()


@app.command(name="all")
def run_all(force_extract: bool = False) -> None:
    """Everything after sampling and prereg: extract, phenology, drivers, analyses, figures."""
    from . import analysis
    from . import extract as ex
    from . import phenology as ph
    from . import drivers as dr
    from . import plots, station

    ex.run(force=force_extract)
    station.run()
    ph.run()
    dr.run()
    if not analysis.CONFIRMATORY.exists():
        analysis.confirmatory()
    analysis.sensitivity()
    analysis.multiverse()
    analysis.parameter_sensitivity()
    analysis.statistical_robustness()
    plots.run()


if __name__ == "__main__":
    app()
