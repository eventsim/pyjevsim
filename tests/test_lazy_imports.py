"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

Regression tests for the package's import footprint.
"""
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Modules needed only to write or restore snapshots. Importing dill alone
# used to account for most of the package's import time.
LAZY_MODULES = ("dill", "json", "ast", "typing")


def _run(code):
    script = (
        "import sys\n"
        f"sys.path.insert(0, {REPO!r})\n"
        f"{code}\n"
        f"print(','.join(m for m in {LAZY_MODULES!r} if m in sys.modules))\n"
    )
    out = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=True
    ).stdout
    return [m for m in out.strip().split(",") if m]


def _loaded_after(code):
    # Ignore modules the interpreter already loads before pyjevsim (a
    # sitecustomize, a .pth hook such as pytest-cov's, an editable-install
    # finder), so the test only flags imports pyjevsim itself triggers.
    baseline = set(_run("pass"))
    return [m for m in _run(code) if m not in baseline]


def test_import_and_run_do_not_load_snapshot_dependencies():
    loaded = _loaded_after(
        "import pyjevsim\n"
        "se = pyjevsim.SysExecutor(1)\n"
        "se.simulate(3, _tm=False)"
    )
    assert loaded == []


def test_snapshot_classes_remain_importable_from_package():
    loaded = _loaded_after(
        "from pyjevsim import SnapshotManager, RestoreHandler\n"
        "from pyjevsim.snapshot_executor import SnapshotExecutor\n"
        "SnapshotManager()"
    )
    assert "dill" not in loaded
