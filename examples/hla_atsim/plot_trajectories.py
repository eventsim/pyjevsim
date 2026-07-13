"""Render top-down (x-y) trajectory plots for the hla_atsim scenarios.

Headless (matplotlib Agg). Reads the deterministic ``standalone_<tag>.csv``
(generating it via ``run_standalone_headless.py`` if missing) and writes
``figures/atsim_<tag>.png``. The federated HLA runs (``run_hla_inprocess.py`` /
``run_hla_pitch.py``) produce byte-identical CSVs, so one figure represents
both the standalone reference and the two-federate co-simulation.

    python examples/hla_atsim/plot_trajectories.py            # both scenarios
    python examples/hla_atsim/plot_trajectories.py stationary # one scenario
"""

from __future__ import annotations

import csv
import os
import subprocess
import sys

import matplotlib
matplotlib.use("Agg")            # headless; never import the GUI pos_plotter
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FIG_DIR = os.path.join(HERE, "figures")
SCENARIOS = ["self_propelled", "stationary"]


def ensure_csv(tag: str) -> str:
    path = os.path.join(HERE, f"standalone_{tag}.csv")
    if not os.path.exists(path):
        subprocess.run(
            [sys.executable, os.path.join(HERE, "run_standalone_headless.py"), tag],
            check=True,
        )
    return path


def load(path: str) -> dict:
    tracks: dict = {}
    with open(path) as f:
        for row in csv.DictReader(f):
            tracks.setdefault(row["object_name"], []).append(
                (int(row["tick"]), float(row["x"]), float(row["y"]))
            )
    for k in tracks:
        tracks[k].sort()
    return tracks


def style(name: str) -> dict:
    if "decoy" in name:
        return dict(color="tab:green", marker="o", kind="decoy", z=3, alpha=0.75)
    if name.startswith("red_torpedo"):
        return dict(color="tab:red", marker="^", kind="torpedo", z=6, alpha=1.0)
    return dict(color="tab:blue", marker="s", kind="surfaceship", z=5, alpha=1.0)


def plot(tag: str) -> str:
    tracks = load(ensure_csv(tag))
    fig, ax = plt.subplots(figsize=(6, 6))
    labelled = set()
    for name, pts in sorted(tracks.items()):
        xs = [p[1] for p in pts]
        ys = [p[2] for p in pts]
        st = style(name)
        lbl = st["kind"] if st["kind"] not in labelled else None
        labelled.add(st["kind"])
        ax.plot(xs, ys, "-", color=st["color"], alpha=st["alpha"],
                linewidth=1.6, zorder=st["z"])
        ax.scatter(xs[0], ys[0], facecolors="white", edgecolors=st["color"],
                   marker="o", s=32, zorder=st["z"] + 1)              # start (hollow)
        ax.scatter(xs[-1], ys[-1], color=st["color"], marker=st["marker"],
                   s=70, zorder=st["z"] + 1, label=lbl)               # end (shape)

    ax.set_title(f"hla_atsim — {tag} decoys (top-down x-y, 30 ticks)")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_aspect("equal", adjustable="datalim")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=8, framealpha=0.9)
    ax.annotate("hollow = start, filled = end",
                xy=(0.02, 0.02), xycoords="axes fraction", fontsize=7,
                color="0.4")

    os.makedirs(FIG_DIR, exist_ok=True)
    out = os.path.join(FIG_DIR, f"atsim_{tag}.png")
    fig.tight_layout()
    fig.savefig(out, dpi=130)
    plt.close(fig)
    print("wrote", out)
    return out


def main() -> None:
    tags = sys.argv[1:] or SCENARIOS
    if tags == ["all"]:
        tags = SCENARIOS
    for t in tags:
        plot(t)


if __name__ == "__main__":
    main()
