from __future__ import annotations

from pathlib import Path

from matplotlib import pyplot as plt
from matplotlib.ticker import MaxNLocator, StrMethodFormatter

from rust_crate_count.crates_io import YearlyCrateCount


def write_chart(rows: list[YearlyCrateCount], dump_timestamp: str, output_stem: Path) -> list[Path]:
    if not rows:
        raise ValueError("rows must not be empty")

    years = [row.year for row in rows]
    active = [row.active_at_jan1 for row in rows]
    new = [row.new_crates for row in rows]
    labels = [str(year) for year in years]
    partial_year = rows[-1].year if rows[-1].partial_year else None

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#333333",
            "axes.labelcolor": "#222222",
            "xtick.color": "#333333",
            "ytick.color": "#333333",
            "text.color": "#222222",
            "axes.titleweight": "bold",
        }
    )

    fig, (ax1, ax2) = plt.subplots(
        2,
        1,
        figsize=(12, 8.5),
        dpi=180,
        gridspec_kw={"height_ratios": [2.2, 1.35]},
    )
    fig.subplots_adjust(left=0.085, right=0.985, top=0.82, bottom=0.13, hspace=0.45)

    fig.text(
        0.085,
        0.955,
        "crates.io crate count by year",
        fontsize=21,
        fontweight="bold",
        ha="left",
        va="top",
    )
    fig.text(
        0.085,
        0.914,
        f"Source: crates.io DB dump, {dump_timestamp}. Includes deleted crates when reconstructing Jan 1 active counts.",
        fontsize=10.5,
        color="#666666",
        ha="left",
        va="top",
    )
    if partial_year is not None:
        fig.text(
            0.085,
            0.887,
            f"{partial_year} is partial through the dump timestamp.",
            fontsize=10.5,
            color="#666666",
            ha="left",
            va="top",
        )

    ax1.plot(
        years,
        active,
        color="#0072B2",
        linewidth=2.8,
        marker="o",
        markersize=5.5,
        markerfacecolor="#D55E00",
        markeredgecolor="white",
        markeredgewidth=1.2,
    )
    ax1.set_title("Active crates at Jan 1", loc="left", fontsize=13, pad=10)
    ax1.set_ylabel("Crates")
    ax1.set_xticks(years, labels)
    ax1.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    ax1.grid(axis="y", color="#e6e8eb", linewidth=0.9)
    ax1.spines[["top", "right"]].set_visible(False)
    for year, count in zip(years, active):
        if year == years[0] or year >= 2018:
            ax1.annotate(
                f"{count:,}",
                (year, count),
                textcoords="offset points",
                xytext=(0, 6),
                ha="center",
                fontsize=8,
            )

    bar_colors = ["#E69F00" if year == partial_year else "#56B4E9" for year in years]
    ax2.bar(years, new, width=0.68, color=bar_colors, edgecolor="#1f6d8f", linewidth=0.7)
    ax2.set_title("New crates created in each year", loc="left", fontsize=13, pad=10)
    ax2.set_ylabel("New crates")
    ax2.set_xticks(years, labels)
    ax2.yaxis.set_major_locator(MaxNLocator(nbins=5, integer=True))
    ax2.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    ax2.grid(axis="y", color="#e6e8eb", linewidth=0.9)
    ax2.spines[["top", "right"]].set_visible(False)
    for year, count in zip(years, new):
        ax2.annotate(
            f"{count:,}",
            (year, count),
            textcoords="offset points",
            xytext=(0, 5),
            ha="center",
            fontsize=8,
        )

    fig.text(
        0.085,
        0.045,
        "Counting rule: crates.created_at plus deleted_crates.created_at; active_at_jan1 subtracts crates deleted before that date.",
        fontsize=9,
        color="#666666",
        ha="left",
    )

    output_stem.parent.mkdir(parents=True, exist_ok=True)
    paths = [output_stem.with_suffix(ext) for ext in [".png", ".pdf", ".svg"]]
    for path in paths:
        fig.savefig(path)
    plt.close(fig)
    return paths
