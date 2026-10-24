"""Subprocess entry point for one timed workload run.

    python -E benchmark/workloads/child.py --repo <checkout> --workload W1
        [--params '{"events": 10}']

``pyjevsim`` (and ``examples`` for W5) are imported from ``--repo``; the
``benchmark`` package (this harness) is loaded from the checkout that holds
this file, under its own name, before ``--repo`` is put on ``sys.path``.  So
base and candidate run identical harness code even when the checkout under
test carries an older or newer ``benchmark/`` directory, and the child
refuses to run if ``pyjevsim`` (or, for a workload that uses it,
``examples``) resolves anywhere but ``--repo``.

The result is one stdout line ``@@SUITE@@ <json>``; anything else a
workload prints is ignored by the parent.
"""

import argparse
import importlib.util
import json
import os
import sys

MARKER = "@@SUITE@@ "

_HERE = os.path.dirname(os.path.abspath(__file__))
_SUITE_ROOT = os.path.dirname(os.path.dirname(_HERE))


def _load_harness():
    """Import this checkout's ``benchmark`` package without its sys.path."""
    pkg_dir = os.path.join(_SUITE_ROOT, "benchmark")
    spec = importlib.util.spec_from_file_location(
        "benchmark", os.path.join(pkg_dir, "__init__.py"),
        submodule_search_locations=[pkg_dir])
    mod = importlib.util.module_from_spec(spec)
    sys.modules["benchmark"] = mod
    spec.loader.exec_module(mod)


def _check_origin(package, repo):
    """Return ``package.__file__``; exit unless it is ``<repo>/<name>/``."""
    path = os.path.abspath(package.__file__ or "")
    if os.path.normcase(os.path.dirname(os.path.dirname(path))) != \
            os.path.normcase(repo):
        raise SystemExit(f"{package.__name__} resolved to {path}, "
                         f"not under {repo}")
    return path


def main(argv=None):
    # Running a script puts its directory first on sys.path; drop it so
    # nothing in benchmark/workloads/ shadows a top-level module.
    if sys.path and os.path.abspath(sys.path[0] or ".") == _HERE:
        sys.path.pop(0)

    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True)
    p.add_argument("--workload", required=True)
    p.add_argument("--params", default="{}")
    p.add_argument("--allow-throttling", action="store_true",
                   help="stay subject to Windows power throttling (EcoQoS)")
    a = p.parse_args(argv)

    _load_harness()
    # Before the timed region: EcoQoS can throttle a process a few seconds
    # in, and a W2 or W5 run can last that long.  No-op off Windows.
    from benchmark.power import disable_power_throttling
    opted_out = False if a.allow_throttling else disable_power_throttling()
    repo = os.path.abspath(a.repo)
    sys.path.insert(0, repo)

    from benchmark.workloads import resolve
    wl = resolve(a.workload)
    if wl.bare_process:
        raise SystemExit(f"{wl.wid} runs as a bare process, not via child.py")
    params = dict(wl.params)
    params.update(json.loads(a.params))

    import pyjevsim
    pj_file = _check_origin(pyjevsim, repo)
    ex_file = None
    if wl.uses_examples:
        import examples
        ex_file = _check_origin(examples, repo)

    module = importlib.import_module(f"benchmark.workloads.{wl.module}")
    result = getattr(module, wl.func)(params)
    result["pyjevsim_file"] = pj_file
    if ex_file is not None:
        result["examples_file"] = ex_file
    result["params"] = params
    result["power_opt_out"] = opted_out
    sys.stdout.write(MARKER + json.dumps(result, sort_keys=True) + "\n")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
