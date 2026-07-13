"""Render trajectory / engagement figures for the hla_atsim scenarios.

Headless (matplotlib Agg). Reads the deterministic ``standalone_<tag>.csv``
(generating it via ``run_standalone_headless.py`` if missing) and writes, per
scenario, three figures under ``figures/``:

  * ``atsim_<tag>.png``        — top-down (x-y) trajectories
  * ``atsim_<tag>_3d.png``     — 3-D (x, y, z) trajectories
  * ``atsim_<tag>_range.png``  — torpedo range to the ship and to each decoy vs. tick

The federated HLA runs (``run_hla_inprocess.py`` / ``run_hla_pitch.py``)
produce byte-identical CSVs, so one set of figures represents both the
standalone reference and the two-federate co-simulation.

    python examples/hla_atsim/plot_trajectories.py            # both scenarios
    python examples/hla_atsim/plot_trajectories.py stationary # one scenario
"""

from __future__ import annotations

import csv
import math
import os
import subprocess
import sys

import matplotlib
matplotlib.use("Agg")            # headless; never import the GUI pos_plotter
import matplotlib.pyplot as plt  # noqa: E402
from mpl_toolkits.mplot3d import Axes3D  # noqa: E402,F401  (registers 3d proj)

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
    """object_name -> sorted list of (tick, x, y, z)."""
    tracks: dict = {}
    with open(path) as f:
        for row in csv.DictReader(f):
            tracks.setdefault(row["object_name"], []).append(
                (int(row["tick"]), float(row["x"]), float(row["y"]), float(row["z"]))
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


def _dist(a, b) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def _save(fig, tag: str, suffix: str) -> str:
    os.makedirs(FIG_DIR, exist_ok=True)
    out = os.path.join(FIG_DIR, f"atsim_{tag}{suffix}.png")
    fig.tight_layout()
    fig.savefig(out, dpi=130)
    plt.close(fig)
    print("wrote", out)
    return out


# ------------------------------------------------------------------ 2-D x-y

def plot_xy(tag: str) -> str:
    tracks = load(ensure_csv(tag))
    fig, ax = plt.subplots(figsize=(6, 6))
    labelled = set()
    for name, pts in sorted(tracks.items()):
        xs = [p[1] for p in pts]
        ys = [p[2] for p in pts]
        st = style(name)
        lbl = st["kind"] if st["kind"] not in labelled else None
        labelled.add(st["kind"])
        ax.plot(xs, ys, "-", color=st["color"], alpha=st["alpha"], linewidth=1.6, zorder=st["z"])
        ax.scatter(xs[0], ys[0], facecolors="white", edgecolors=st["color"], marker="o", s=32, zorder=st["z"] + 1)
        ax.scatter(xs[-1], ys[-1], color=st["color"], marker=st["marker"], s=70, zorder=st["z"] + 1, label=lbl)
    ax.set_title(f"hla_atsim - {tag} decoys (top-down x-y, 30 ticks)")
    ax.set_xlabel("x"); ax.set_ylabel("y")
    ax.set_aspect("equal", adjustable="datalim")
    ax.grid(True, alpha=0.3); ax.legend(loc="best", fontsize=8, framealpha=0.9)
    ax.annotate("hollow = start, filled = end", xy=(0.02, 0.02), xycoords="axes fraction", fontsize=7, color="0.4")
    return _save(fig, tag, "")


# ------------------------------------------------------------------- 3-D

def plot_3d(tag: str) -> str:
    tracks = load(ensure_csv(tag))
    fig = plt.figure(figsize=(6.5, 6))
    ax = fig.add_subplot(111, projection="3d")
    labelled = set()
    for name, pts in sorted(tracks.items()):
        xs = [p[1] for p in pts]; ys = [p[2] for p in pts]; zs = [p[3] for p in pts]
        st = style(name)
        lbl = st["kind"] if st["kind"] not in labelled else None
        labelled.add(st["kind"])
        ax.plot(xs, ys, zs, "-", color=st["color"], alpha=st["alpha"], linewidth=1.6)
        ax.scatter(xs[0], ys[0], zs[0], facecolors="white", edgecolors=st["color"], marker="o", s=28)
        ax.scatter(xs[-1], ys[-1], zs[-1], color=st["color"], marker=st["marker"], s=55, label=lbl)
    ax.set_title(f"hla_atsim - {tag} decoys (3-D, 30 ticks)")
    ax.set_xlabel("x"); ax.set_ylabel("y"); ax.set_zlabel("z (depth)")
    ax.legend(loc="upper left", fontsize=8)
    ax.view_init(elev=22, azim=-60)
    return _save(fig, tag, "_3d")


# ------------------------------------------------------- range vs. time

def plot_range(tag: str) -> str:
    tracks = load(ensure_csv(tag))
    torp_name = next((n for n in tracks if n.startswith("red_torpedo")), None)
    ship_name = next((n for n in tracks if n.startswith("blue_ship") and "decoy" not in n), None)
    if torp_name is None:
        raise SystemExit("no torpedo track")
    torp = {t: (x, y, z) for (t, x, y, z) in tracks[torp_name]}

    fig, ax = plt.subplots(figsize=(7, 4.5))
    # torpedo -> ship
    if ship_name:
        ship = {t: (x, y, z) for (t, x, y, z) in tracks[ship_name]}
        ts = sorted(set(torp) & set(ship))
        ax.plot(ts, [_dist(torp[t], ship[t]) for t in ts], "-", color="tab:blue",
                linewidth=2.4, label="to surfaceship", zorder=5)
    # torpedo -> each decoy
    first = True
    for name in sorted(n for n in tracks if "decoy" in n):
        d = {t: (x, y, z) for (t, x, y, z) in tracks[name]}
        ts = sorted(set(torp) & set(d))
        if not ts:
            continue
        ax.plot(ts, [_dist(torp[t], d[t]) for t in ts], "-", color="tab:green",
                linewidth=1.3, alpha=0.8, label="to decoys" if first else None)
        first = False
    ax.axhline(0, color="0.7", linewidth=0.8)
    ax.set_title(f"hla_atsim - {tag} decoys: torpedo range vs. tick")
    ax.set_xlabel("tick"); ax.set_ylabel("3-D distance to torpedo")
    ax.grid(True, alpha=0.3); ax.legend(loc="best", fontsize=8)
    return _save(fig, tag, "_range")


def main() -> None:
    tags = sys.argv[1:] or SCENARIOS
    if tags == ["all"]:
        tags = SCENARIOS
    for t in tags:
        plot_xy(t)
        plot_3d(t)
        plot_range(t)


if __name__ == "__main__":
    main()
