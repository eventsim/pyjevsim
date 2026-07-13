"""Scenario loading + platform construction, ctx-injected (no singleton)."""

import yaml

from model.surfaceship import SurfaceShip
from model.torpedo import Torpedo


def load_scenario(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)


def build_ship(name, data, ctx):
    """data = one entry of yaml['SurfaceShip']."""
    return SurfaceShip(name, data, ctx)


def build_torpedo(name, data, ctx):
    """data = one entry of yaml['Torpedo']."""
    return Torpedo(name, data, ctx)
