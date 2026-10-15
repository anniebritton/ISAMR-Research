"""Figure: autoresearch search dynamics and the synthetic-vs-real trade-off."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from wapusk_greenup import config
from wapusk_greenup.plots import GRID, INK_2, SERIES, SURFACE, _save

HERE = Path(__file__).resolve().parent


def main() -> None:
    rows = [json.loads(line) for line in (HERE / "ledger.jsonl").read_text().splitlines()]
    led = pd.DataFrame(rows)
    abl = pd.read_csv(config.TABLES / "autoresearch_ablation.csv")

    fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.8), gridspec_kw={"width_ratios": [1.3, 1]})
    scored = led[led["score"].notna()]
    start_score = 3.1824  # starting candidate (= pre-registered SG), scored before iteration 1
    best = scored["score"].cummin().clip(upper=start_score)
    a.plot(scored["iteration"], best, color=SERIES[0], lw=1.5, drawstyle="steps-post", label="Best score so far")
    rev = scored[~scored["kept"]]
    a.scatter(rev["iteration"], rev["score"].clip(upper=3.7), s=18, color=GRID, edgecolor=INK_2, linewidth=0.6,
              label="Reverted (clipped at 3.7)")
    kept = scored[scored["kept"]]
    a.scatter(kept["iteration"], kept["score"], s=30, color=SERIES[1], edgecolor=SURFACE, linewidth=1, zorder=3,
              label="Kept")
    noedit = led[led["score"].isna()]["iteration"]
    a.scatter(noedit, np.full(len(noedit), 3.68), marker="x", s=24, color=INK_2, label="Agent made no edit")
    a.axvline(3.5, color=INK_2, lw=0.8, ls=":")
    a.text(3.7, 3.62, "smoke test | main run", fontsize=7, color=INK_2)
    a.set_xlabel("Iteration")
    a.set_ylabel("Visible score (days, lower is better)")
    a.set_title("Search dynamics")
    a.axhline(start_score, color=INK_2, lw=0.8, ls="--")
    a.text(10.5, start_score + 0.02, "starting score (pre-registered SG)", fontsize=7, color=INK_2)
    a.legend(frameon=False, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=4)

    main_versions = abl[~abl["version"].str.startswith("final without")]
    b.plot(main_versions["heldout_error"], main_versions["parkwide_annual_r"], color=GRID, lw=1, zorder=1)
    for _, r in abl.iterrows():
        is_ablation = r["version"].startswith("final without")
        color = SERIES[2] if is_ablation else SERIES[0]
        b.scatter(r["heldout_error"], r["parkwide_annual_r"], s=28, color=color, edgecolor=SURFACE, linewidth=1, zorder=2)
    for name, dx, dy in [("start (= pre-registered SG)", 0.01, 0.001), ("iter 8", 0.01, 0.0015), ("iter 16", 0.008, 0.0012)]:
        r = abl[abl["version"] == name].iloc[0]
        b.annotate(name.replace(" (= pre-registered SG)", " (pre-registered SG)"), (r["heldout_error"], r["parkwide_annual_r"]),
                   xytext=(r["heldout_error"] + dx, r["parkwide_annual_r"] + dy), fontsize=7, color=INK_2)
    b.scatter([], [], color=SERIES[0], s=28, label="Kept version (in order)")
    b.scatter([], [], color=SERIES[2], s=28, label="Final minus one change")
    b.set_xlabel("Held-out synthetic error (days)")
    b.set_ylabel("Park-wide annual r with MCD12Q2")
    b.set_title("What carried over to real data")
    b.legend(frameon=False, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=2)
    fig.tight_layout()
    _save(fig, "autoresearch_dynamics")


CATEGORY_LABELS = {
    "snow_and_melt": "Snow and melt handling",
    "smoother": "Smoother settings",
    "amplitude": "Amplitude estimate",
    "crossing_rule": "Crossing rule",
    "ensemble": "Combining extractors",
    "outlier_filter": "Outlier filter",
    "validity_threshold": "Validity thresholds",
    "line_count": "Line-count cleanup",
    "no_edit": "No edit",
}


def attempts() -> None:
    """Each iteration placed by the kind of change the agent attempted (coded from its rationales)."""
    rows = pd.read_csv(HERE / "iteration_coding.csv")
    order = list(CATEGORY_LABELS)
    y = {c: i for i, c in enumerate(reversed(order))}
    fig, ax = plt.subplots(figsize=(9, 3.6))
    for outcome, style in {
        "reverted": dict(color=GRID, edgecolor=INK_2, linewidth=0.7, s=42, marker="o", label="Reverted"),
        "kept": dict(color=SERIES[1], edgecolor=SURFACE, linewidth=1, s=56, marker="o", label="Kept"),
        "no edit": dict(color=INK_2, s=40, marker="x", label="No edit"),
    }.items():
        sub = rows[rows["outcome"] == outcome]
        ax.scatter(sub["iteration"], sub["category"].map(y), zorder=3, **style)
    ax.set_yticks(list(y.values()), [CATEGORY_LABELS[c] for c in y])
    ax.set_xlabel("Iteration")
    ax.set_xlim(0, 34)
    ax.grid(axis="x", visible=False)
    ax.set_title("What the agent tried, by iteration")
    ax.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=3)
    fig.tight_layout()
    _save(fig, "autoresearch_attempts")


if __name__ == "__main__":
    main()
    attempts()
