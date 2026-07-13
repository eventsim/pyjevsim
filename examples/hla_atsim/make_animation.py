"""Render an animated GIF of an hla_atsim engagement (top-down x-y).

Headless (matplotlib Agg + PillowWriter). Reads the deterministic
``standalone_<tag>.csv`` (generating it via ``run_standalone_headless.py`` if
missing) and writes ``figures/atsim_<tag>.gif`` — the surfaceship, torpedo and
decoys advancing tick by tick with growing trails. The federated HLA runs
produce byte-identical CSVs, so the animation represents both.

    python examples/hla_atsim/make_animation.py            # both scenarios
    python examples/hla_atsim/make_animation.py stationary # one scenario
"""

from __future__ import annotations

import os
import sys

import matplotlib
matplotlib.use("Agg")            # headless
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.animation import FuncAnimation, PillowWriter  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from plot_trajectories import ensure_csv, load, style, FIG_DIR, SCENARIOS  # noqa: E402

FPS = 5          # 200 ms / frame
HOLD_FRAMES = 6  # repeat the last tick so the outcome is readable


def make_gif(tag: str) -> str:
    tracks = load(ensure_csv(tag))
    ticks = sorted({p[0] for pts in tracks.values() for p in pts})
    all_x = [p[1] for pts in tracks.values() for p in pts]
    all_y = [p[2] for pts in tracks.values() for p in pts]
    mx = (max(all_x) - min(all_x)) * 0.06 + 3
    my = (max(all_y) - min(all_y)) * 0.06 + 3

    # Size the figure to the data aspect (keeps equal-scale axes without a
    # tall letterbox). x-range is much wider than y-range in these scenarios.
    dx = (max(all_x) + mx) - (min(all_x) - mx)
    dy = (max(all_y) + my) - (min(all_y) - my)
    fig_w = 7.0
    fig_h = max(3.2, min(6.5, fig_w * dy / dx + 1.1))  # +1.1 for title/labels
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_xlim(min(all_x) - mx, max(all_x) + mx)
    ax.set_ylim(min(all_y) - my, max(all_y) + my)
    ax.set_aspect("equal")
    ax.set_xlabel("x"); ax.set_ylabel("y")
    ax.grid(True, alpha=0.3)

    # One trail line + one marker per object; a static legend by kind.
    artists = {}
    labelled = set()
    for name in sorted(tracks):
        st = style(name)
        lbl = st["kind"] if st["kind"] not in labelled else None
        labelled.add(st["kind"])
        trail, = ax.plot([], [], "-", color=st["color"], alpha=st["alpha"] * 0.8, linewidth=1.4)
        marker, = ax.plot([], [], linestyle="none", marker=st["marker"], color=st["color"],
                          markersize=9 if st["kind"] != "decoy" else 7, label=lbl)
        artists[name] = (trail, marker)
    ax.legend(loc="upper right", fontsize=8, framealpha=0.9)
    title = ax.set_title("")
    fig.tight_layout()

    frames = list(ticks) + [ticks[-1]] * HOLD_FRAMES

    def update(t):
        for name, pts in tracks.items():
            seq = [p for p in pts if p[0] <= t]
            trail, marker = artists[name]
            if seq:
                trail.set_data([p[1] for p in seq], [p[2] for p in seq])
                marker.set_data([seq[-1][1]], [seq[-1][2]])
            else:
                trail.set_data([], []); marker.set_data([], [])
        title.set_text(f"hla_atsim - {tag} decoys   (tick {t}/{ticks[-1]})")
        out = [a for pair in artists.values() for a in pair]
        return out + [title]

    anim = FuncAnimation(fig, update, frames=frames, interval=1000 / FPS, blit=False)
    os.makedirs(FIG_DIR, exist_ok=True)
    path = os.path.join(FIG_DIR, f"atsim_{tag}.gif")
    anim.save(path, writer=PillowWriter(fps=FPS))
    plt.close(fig)
    print("wrote", path, f"({os.path.getsize(path) // 1024} KB)")
    return path


def main() -> None:
    tags = sys.argv[1:] or SCENARIOS
    if tags == ["all"]:
        tags = SCENARIOS
    for t in tags:
        make_gif(t)


if __name__ == "__main__":
    main()
