"""Standard performance suite (roadmap INF-2).

Runs the workloads W1..W7 (see ``benchmark/workloads/__init__.py``) against
one checkout, or against a base and a candidate checkout interleaved round
by round, every timed run in a fresh subprocess, and reports simulation time
only (model build excluded) with each run's parity key.

A/B mode::

    python -m benchmark.suite --base <checkout> --cand <checkout> \\
        --rounds 5 --workloads W1,W3 --out results.json [--markdown]

Single-checkout mode (``--repo`` defaults to the checkout holding this
file)::

    python -m benchmark.suite --repo <checkout> --rounds 5

Measurement rules (docs/source/benchmark.rst, "Standard Performance Suite"):

* Every timed run is a fresh process.  Never compare before/after inside
  one process: the effect of the SystemObject class-attribute fix (#41)
  reads as zero there.
* In A/B mode each round runs base and candidate back to back for every
  workload, alternating which goes first (round 0 base first, round 1
  candidate first, ...), so slow drift of the machine hits both sides.
* The headline number is the ratio of minimums, ``min(cand) / min(base)``
  (below 1.0 means the candidate is faster).  The median of the per-round
  paired ratios and their min..max spread are reported next to it.
* A run is only timed against another when their parity keys (transition
  counts or model-level result counters) are identical; otherwise the
  workload is reported as REFUSED and the exit status is 3.
* Differences under the noise floor (default 5%) are reported as "noise",
  never as a speed-up or a regression.

``--pin`` restricts the suite and every child to a CPU set (a mask such as
``0xFFFF``, a list such as ``0-15`` or ``0,2,4``; a bare integer is a mask,
so ``5`` means CPUs 0 and 2): SetProcessAffinityMask on Windows (CPUs 0-63
only, one processor group), ``os.sched_setaffinity`` on Linux.  There is no default mask,
because which cores are the fast ones is machine specific (on the
i7-12700 used for the 2026-10 records the P-core threads are 0-15).
"""

import argparse
import datetime
import json
import os
import platform
import statistics
import struct
import subprocess
import sys
import time

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from benchmark.workloads import DEFAULT_WORKLOADS, resolve  # noqa: E402
from benchmark.workloads import startup as _startup  # noqa: E402

MARKER = "@@SUITE@@ "
SUITE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHILD = os.path.join(SUITE_ROOT, "benchmark", "workloads", "child.py")
DEFAULT_NOISE_FLOOR = 0.05


class ChildError(RuntimeError):
    pass


# --------------------------------------------------------------------------
# CPU affinity
# --------------------------------------------------------------------------

def cpu_limit():
    """How many CPU indices ``--pin`` may name on this machine.

    ``os.cpu_count()``, and on Windows at most the width of a pointer (64
    on 64-bit Python): ``SetProcessAffinityMask`` takes one processor
    group's mask as a pointer-sized integer, so a higher index would be
    silently cut off the mask instead of rejected.
    """
    limit = os.cpu_count() or 1
    if sys.platform == "win32":
        limit = min(limit, 8 * struct.calcsize("P"))
    return limit


def check_cpus(cpus, limit=None):
    """Raise ``ValueError`` unless every index is in ``0 .. limit - 1``."""
    limit = cpu_limit() if limit is None else limit
    bad = sorted(c for c in cpus if not 0 <= c < limit)
    if bad:
        why = (" (SetProcessAffinityMask covers one processor group)"
               if sys.platform == "win32" and bad[-1] >= 64 else "")
        raise ValueError(f"CPU index {bad[-1]} is out of range: this machine "
                         f"accepts 0-{limit - 1}{why}")
    return cpus


def parse_cpu_set(text, limit=None):
    """``0xFFFF`` / ``65535`` (a mask) or ``0-15`` / ``0,2,4-7`` (a list).

    A bare integer is a mask, as in ``taskset``: ``5`` selects CPUs 0 and
    2, not CPU 5 (write ``5-5`` for that).  Returns a sorted list of CPU
    indices; with ``limit``, raises ``ValueError`` for an index at or above
    it (see ``cpu_limit``).
    """
    text = text.strip()
    if not text:
        raise ValueError("empty CPU set")
    if text.lower().startswith("0x"):
        mask = int(text, 16)
        cpus = [i for i in range(mask.bit_length()) if mask >> i & 1]
    elif "-" in text or "," in text:
        cpus = set()
        for part in text.split(","):
            part = part.strip()
            if "-" in part:
                lo, hi = (int(x) for x in part.split("-", 1))
                if hi < lo:
                    raise ValueError(f"bad CPU range {part!r}")
                cpus.update(range(lo, hi + 1))
            elif part:
                cpus.add(int(part))
        cpus = sorted(cpus)
    else:
        # A bare integer is a mask, like taskset's default reading.
        mask = int(text)
        cpus = [i for i in range(mask.bit_length()) if mask >> i & 1]
    if not cpus:
        raise ValueError(f"CPU set {text!r} selects no CPU")
    if limit is not None:
        check_cpus(cpus, limit)
    return cpus


def _cpus_to_mask(cpus):
    mask = 0
    for c in cpus:
        mask |= 1 << c
    return mask


def set_affinity(cpus, process=None):
    """Pin this process (``process=None``) or a ``subprocess.Popen`` child.

    Raises ``ValueError`` for an index outside ``cpu_limit()`` (before any
    platform call), ``OSError`` when the platform call fails and
    ``NotImplementedError`` on platforms without an affinity API (macOS).
    """
    check_cpus(cpus)
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.SetProcessAffinityMask.argtypes = (wintypes.HANDLE, ctypes.c_size_t)
        k32.SetProcessAffinityMask.restype = wintypes.BOOL
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        handle = (k32.GetCurrentProcess() if process is None
                  else int(process._handle))
        if not k32.SetProcessAffinityMask(handle, _cpus_to_mask(cpus)):
            raise ctypes.WinError(ctypes.get_last_error())
        return
    if hasattr(os, "sched_setaffinity"):
        os.sched_setaffinity(0 if process is None else process.pid, set(cpus))
        return
    raise NotImplementedError(f"CPU pinning is not supported on {sys.platform}")


# --------------------------------------------------------------------------
# Running one measurement
# --------------------------------------------------------------------------

def run_once(wid, repo, python=sys.executable, params=None, cpus=None,
             timeout=900):
    """Run workload ``wid`` once against ``repo`` in a fresh process."""
    wl = resolve(wid)
    params = dict(params or {})
    if wl.bare_process:
        argv = _startup.command(python, repo, params)
    else:
        argv = [python, "-E", CHILD, "--repo", repo, "--workload", wl.wid,
                "--params", json.dumps(params)]
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env["PYTHONIOENCODING"] = "utf-8"
    t0 = time.perf_counter()
    proc = subprocess.Popen(argv, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, cwd=SUITE_ROOT, env=env,
                            text=True, encoding="utf-8", errors="replace")
    if cpus is not None:
        # The child also inherited the parent's mask; this makes the
        # restriction explicit and covers a parent that was not pinned.
        try:
            set_affinity(cpus, proc)
        except (OSError, ProcessLookupError):
            pass   # the child may already have exited
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, err = proc.communicate()
        raise ChildError(f"{wid} on {repo}: timed out after {timeout}s")
    wall = time.perf_counter() - t0
    payload = None
    for line in out.splitlines():
        if line.startswith(MARKER):
            payload = json.loads(line[len(MARKER):])
    if proc.returncode != 0 or payload is None:
        tail = "\n".join((err or out).strip().splitlines()[-15:])
        raise ChildError(
            f"{wid} on {repo}: exit {proc.returncode}, no result\n{tail}")
    if wl.bare_process:
        payload = _startup.result_from(payload, wall)
    pj = os.path.normcase(os.path.abspath(payload["pyjevsim_file"]))
    if not pj.startswith(os.path.normcase(os.path.abspath(repo)) + os.sep):
        raise ChildError(f"{wid}: pyjevsim came from {pj}, not {repo}")
    return payload


# --------------------------------------------------------------------------
# Statistics
# --------------------------------------------------------------------------

def _side_stats(values):
    lo, hi = min(values), max(values)
    return {"min": lo, "median": statistics.median(values), "max": hi,
            "spread": (hi - lo) / lo if lo else 0.0, "n": len(values)}


def verdict(ratio_min, median_ratio, floor):
    if abs(ratio_min - 1.0) < floor:
        return "noise"
    faster = ratio_min < 1.0
    if (median_ratio < 1.0) != faster or abs(median_ratio - 1.0) < floor:
        return "unclear"
    return "faster" if faster else "slower"


def compare_metric(base_vals, cand_vals, floor=DEFAULT_NOISE_FLOOR):
    """Summarise one metric of an interleaved A/B run (cand / base)."""
    paired = [c / b for b, c in zip(base_vals, cand_vals) if b > 0]
    ratio_min = min(cand_vals) / min(base_vals)
    median_ratio = statistics.median(paired)
    return {
        "base": _side_stats(base_vals),
        "cand": _side_stats(cand_vals),
        "ratio_of_min": ratio_min,
        "speedup_of_min": 1.0 / ratio_min,
        "median_ratio": median_ratio,
        "ratio_spread": [min(paired), max(paired)],
        "verdict": verdict(ratio_min, median_ratio, floor),
    }


def check_parity(runs_by_side):
    """Return ``(ok, reason, key)`` for runs ``{side: [run, ...]}``."""
    keys = {}
    for side, runs in runs_by_side.items():
        side_keys = {json.dumps(r["parity"], sort_keys=True) for r in runs}
        if len(side_keys) != 1:
            return False, f"{side} runs disagree: {sorted(side_keys)}", None
        keys[side] = side_keys.pop()
    distinct = set(keys.values())
    if len(distinct) != 1:
        detail = "; ".join(f"{s}={k}" for s, k in keys.items())
        return False, f"parity keys differ: {detail}", None
    return True, "", json.loads(distinct.pop())


# --------------------------------------------------------------------------
# Suite driver
# --------------------------------------------------------------------------

def _git_head(path):
    if not os.path.exists(os.path.join(path, ".git")):
        return None
    try:
        out = subprocess.run(["git", "-C", path, "rev-parse", "HEAD"],
                             capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() or None


def _log(msg, quiet):
    if not quiet:
        print(msg, file=sys.stderr, flush=True)


def run_suite(sides, workloads, rounds=5, warmup=1, python=sys.executable,
              params=None, cpus=None, floor=DEFAULT_NOISE_FLOOR,
              timeout=900, quiet=False):
    """Run the suite.

    ``sides`` is an ordered dict ``{label: checkout}`` with one entry
    (single mode) or two (``base`` first, then ``cand``).  Returns the
    result document written by ``--out``.
    """
    params = params or {}
    labels = list(sides)
    doc = {
        "suite": "pyjevsim standard performance suite (INF-2)",
        "started": datetime.datetime.now().isoformat(timespec="seconds"),
        "mode": "ab" if len(labels) == 2 else "single",
        "rounds": rounds,
        "warmup": warmup,
        "noise_floor": floor,
        "pin": cpus,
        "environment": {
            "python": sys.version,
            "executable": python,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "cpu_count": os.cpu_count(),
        },
        "sides": {lab: {"path": os.path.abspath(p), "git_head": _git_head(p)}
                  for lab, p in sides.items()},
        "workloads": {},
    }
    for wid in workloads:
        wl = resolve(wid)
        merged = dict(wl.params)
        merged.update(params.get(wl.wid, {}))
        doc["workloads"][wl.wid] = {"title": wl.title, "params": merged,
                                    "metrics": list(wl.metrics),
                                    "runs": {lab: [] for lab in labels}}

    # Warm-up: untimed, one per (workload, side); compiles __pycache__ and
    # fails fast on a broken checkout.
    for wid in doc["workloads"]:
        for lab in labels:
            for _ in range(warmup):
                _log(f"warm-up {wid} {lab}", quiet)
                run_once(wid, sides[lab], python, params.get(wid), cpus,
                         timeout)

    for r in range(rounds):
        order = labels if r % 2 == 0 else labels[::-1]
        for wid, entry in doc["workloads"].items():
            for lab in order:
                res = run_once(wid, sides[lab], python, params.get(wid),
                               cpus, timeout)
                res["round"] = r
                res["position"] = order.index(lab)
                entry["runs"][lab].append(res)
                head = entry["metrics"][0]
                _log(f"round {r + 1}/{rounds} {wid} {lab:>4}: "
                     f"{head} {res['metrics'][head] * 1e3:9.2f} ms", quiet)

    status = 0
    for wid, entry in doc["workloads"].items():
        ok, reason, key = check_parity(entry["runs"])
        entry["parity_ok"] = ok
        entry["parity"] = key
        entry["refused"] = None if ok else reason
        entry["summary"] = {}
        if not ok:
            status = 3
            continue
        for metric in entry["metrics"]:
            vals = {lab: [run["metrics"][metric] for run in entry["runs"][lab]]
                    for lab in labels}
            if len(labels) == 2:
                entry["summary"][metric] = compare_metric(
                    vals[labels[0]], vals[labels[1]], floor)
            else:
                entry["summary"][metric] = _side_stats(vals[labels[0]])
    doc["finished"] = datetime.datetime.now().isoformat(timespec="seconds")
    doc["status"] = status
    return doc


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------

def _ms(x):
    return f"{x * 1e3:.2f}"


def _pct(x):
    return f"{x * 100:.1f}%"


def format_report(doc, markdown=False):
    lines = []
    ab = doc["mode"] == "ab"
    sides = doc["sides"]
    labels = list(sides)
    if markdown:
        lines.append(f"Rounds: {doc['rounds']}, noise floor "
                     f"{_pct(doc['noise_floor'])}, pin: {doc['pin']}")
        for lab, info in sides.items():
            head = f" ({info['git_head'][:10]})" if info["git_head"] else ""
            lines.append(f"- {lab}: `{info['path']}`{head}")
        lines.append("")
        if ab:
            lines.append("| workload | metric | base min ms | cand min ms | "
                         "cand/base (min) | median ratio [spread] | "
                         "base / cand spread | verdict |")
            lines.append("|---|---|---:|---:|---:|---|---|---|")
        else:
            lines.append("| workload | metric | min ms | median ms | "
                         "max ms | spread |")
            lines.append("|---|---|---:|---:|---:|---:|")
    for wid, entry in doc["workloads"].items():
        if not entry["parity_ok"]:
            msg = f"REFUSED: {entry['refused']}"
            lines.append(f"| {wid} | - | {msg} |" if markdown
                         else f"{wid:<3} {msg}")
            continue
        for metric, s in entry["summary"].items():
            if ab:
                row = [wid, metric, _ms(s["base"]["min"]), _ms(s["cand"]["min"]),
                       f"{s['ratio_of_min']:.3f}",
                       f"{s['median_ratio']:.3f} [{s['ratio_spread'][0]:.3f}"
                       f"..{s['ratio_spread'][1]:.3f}]",
                       f"{_pct(s['base']['spread'])} / {_pct(s['cand']['spread'])}",
                       s["verdict"]]
            else:
                row = [wid, metric, _ms(s["min"]), _ms(s["median"]),
                       _ms(s["max"]), _pct(s["spread"])]
            if markdown:
                lines.append("| " + " | ".join(row) + " |")
            else:
                lines.append("  ".join(f"{c:>12}" if i > 1 else f"{c:<10}"
                                       for i, c in enumerate(row)))
    if not markdown:
        if ab:
            header = ["workload", "metric", "base_min_ms", "cand_min_ms",
                      "cand/base", "median[spread]", "spread b/c", "verdict"]
        else:
            header = ["workload", "metric", "min_ms", "median_ms", "max_ms",
                      "spread"]
        lines.insert(0, "  ".join(f"{c:>12}" if i > 1 else f"{c:<10}"
                                  for i, c in enumerate(header)))
        lines.insert(1, "-" * len(lines[0]))
        lines.insert(0, f"labels: {', '.join(labels)}; rounds {doc['rounds']}; "
                        f"cand/base < 1 means the candidate is faster")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _parse_params(items):
    """``W3.count=200`` -> {"W3": {"count": 200}} (values parsed as JSON)."""
    out = {}
    for item in items or []:
        key, _, value = item.partition("=")
        wid, _, name = key.partition(".")
        if not name or not _:
            raise ValueError(f"--param expects W<n>.name=value, got {item!r}")
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            parsed = value
        out.setdefault(resolve(wid).wid, {})[name] = parsed
    return out


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog="python -m benchmark.suite",
        description="pyjevsim standard performance suite (fresh process per "
                    "run, interleaved A/B, parity-checked)")
    p.add_argument("--base", help="base checkout (A/B mode)")
    p.add_argument("--cand", help="candidate checkout (A/B mode)")
    p.add_argument("--repo", help="checkout for single mode (default: the "
                                  "checkout that holds this suite)")
    p.add_argument("--rounds", type=int, default=5)
    p.add_argument("--warmup", type=int, default=1,
                   help="untimed runs per workload and side (default 1)")
    p.add_argument("--workloads", default=",".join(DEFAULT_WORKLOADS),
                   help="comma-separated ids (default: all, W1..W7)")
    p.add_argument("--param", action="append", default=[],
                   metavar="W<n>.NAME=VALUE",
                   help="override a workload parameter, e.g. W3.count=2000")
    p.add_argument("--python", default=sys.executable,
                   help="interpreter for the child processes")
    p.add_argument("--pin", default=None, metavar="CPUS",
                   help="CPU mask (0xFFFF; a bare integer is a mask too, "
                        "so 5 means CPUs 0 and 2) or list (0-15, 0,2,4) "
                        "for the suite and every child; no default")
    p.add_argument("--noise-floor", type=float, default=DEFAULT_NOISE_FLOOR)
    p.add_argument("--timeout", type=int, default=900,
                   help="seconds per child run")
    p.add_argument("--out", help="write the full JSON result here")
    p.add_argument("--markdown", action="store_true",
                   help="print the summary as a Markdown table")
    p.add_argument("--list", action="store_true",
                   help="list the workloads and exit")
    p.add_argument("--quiet", action="store_true")
    a = p.parse_args(argv)
    if (a.base is None) != (a.cand is None):
        p.error("--base and --cand go together")
    if a.base and a.repo:
        p.error("use either --base/--cand or --repo")
    if a.rounds < 1:
        p.error("--rounds must be >= 1")
    return a


def main(argv=None):
    a = parse_args(argv)
    if a.list:
        from benchmark.workloads import WORKLOADS
        for wl in WORKLOADS.values():
            print(f"{wl.wid}  {wl.title}\n     params: {wl.params}  "
                  f"metrics: {', '.join(wl.metrics)}")
        return 0
    try:
        workloads = [resolve(w.strip()).wid for w in a.workloads.split(",")
                     if w.strip()]
        params = _parse_params(a.param)
        cpus = parse_cpu_set(a.pin, cpu_limit()) if a.pin else None
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if a.base:
        sides = {"base": a.base, "cand": a.cand}
    else:
        sides = {"repo": a.repo or SUITE_ROOT}
    for lab, path in sides.items():
        if not os.path.isfile(os.path.join(path, "pyjevsim", "__init__.py")):
            print(f"error: {lab} checkout {path!r} has no pyjevsim package",
                  file=sys.stderr)
            return 2
    if cpus is not None:
        try:
            set_affinity(cpus)
        except (OSError, NotImplementedError, ValueError) as exc:
            print(f"error: cannot pin to {a.pin}: {exc}", file=sys.stderr)
            return 2
    try:
        doc = run_suite(sides, workloads, rounds=a.rounds, warmup=a.warmup,
                        python=a.python, params=params, cpus=cpus,
                        floor=a.noise_floor, timeout=a.timeout, quiet=a.quiet)
    except ChildError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(format_report(doc, markdown=a.markdown))
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".",
                    exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=1, sort_keys=False)
            f.write("\n")
        _log(f"wrote {a.out}", a.quiet)
    return doc["status"]


if __name__ == "__main__":
    raise SystemExit(main())
