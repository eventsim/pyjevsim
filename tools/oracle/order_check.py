#!/usr/bin/env python
"""Check whether same-time processing order is reproducible.

The trace oracle sorts the events of an instant, so it cannot see the order
in which the engine processed same-time models.  This tool runs scenarios
once per executor-hash salt, each in a fresh subprocess, and compares the
traces WITHOUT sorting inside an instant:

* ``order stable``: the unsorted trace is identical under every salt; the
  engine's same-time order does not depend on set iteration here.
* ``order varies``: the processing order changes with the salt.  The
  ``outcome`` column then says whether the order-insensitive (sorted) hash
  changes as well, i.e. whether the scenario's results depend on that order.

    python tools/oracle/order_check.py [--repo <checkout>] [--salts 1,2,3,4,5,6]
                                       [--scenarios a,b,... | --all] [--jobs 4]
                                       [--vary-hashseed] [--json <report.json>]

Only the informational scenarios run by default.  ``--vary-hashseed`` also
sets ``PYTHONHASHSEED`` to the salt, so str-keyed sets and dicts in models
change order too.  This is a diagnostic, not a CI gate.
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import trace_oracle as oracle  # noqa: E402


def _first_difference(a, b):
    """Index and (engine, instant) header of the first differing line."""
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return i, json.loads(x)[:2]
    if len(a) != len(b):
        i = min(len(a), len(b))
        return i, json.loads((a if len(a) > i else b)[i])[:2]
    return None


def check(repo, names, salts, jobs, vary_hashseed):
    runs = {}           # name -> [(salt, raw_sha, sorted_sha, error)]
    first_raw = {}      # name -> raw lines of the first salt
    diff_at = {}
    for s in salts:
        results, wall = oracle.run_scenarios(repo, names, jobs, salt=s, raw_order=True,
                                             hashseed=str(s) if vary_hashseed else "0")
        print("salt %s: %d scenarios in %.1f s" % (s, len(names), wall), file=sys.stderr)
        for n in names:
            r = results[n]
            raw = r.get("raw_lines") or []
            raw_sha, _ = oracle.scenario_hash(raw, r.get("final"), r.get("error"))
            sorted_sha, _ = oracle.scenario_hash(r.get("lines") or [], r.get("final"), r.get("error"))
            err = (r.get("error") or "").split("\n")[0] or None
            runs.setdefault(n, []).append((s, raw_sha, sorted_sha, err))
            if n not in first_raw:
                first_raw[n] = raw
            elif n not in diff_at and raw != first_raw[n]:
                diff_at[n] = (s, _first_difference(first_raw[n], raw))
    report = {}
    for n in names:
        rs = runs[n]
        report[n] = {
            "informational": oracle.SC_BY_NAME[n][1],
            "order_stable": len({x[1] for x in rs}) == 1,
            "outcome_stable": len({x[2] for x in rs}) == 1,
            "errors": sorted({x[3] for x in rs if x[3]}),
            "salts": {str(x[0]): {"raw_sha256": x[1], "sorted_sha256": x[2]} for x in rs},
        }
        if n in diff_at:
            s, (i, head) = diff_at[n]
            report[n]["first_order_difference"] = {"salt": s, "group": i, "engine": head[0], "instant": head[1]}
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description="same-time order reproducibility check (unsorted traces)")
    ap.add_argument("--repo", default=oracle.DEFAULT_REPO)
    ap.add_argument("--salts", default="1,2,3,4,5,6")
    ap.add_argument("--scenarios", default="", help="comma-separated (default: the informational scenarios)")
    ap.add_argument("--all", action="store_true", help="check every scenario")
    ap.add_argument("--jobs", type=int, default=min(4, os.cpu_count() or 1))
    ap.add_argument("--vary-hashseed", action="store_true", help="also set PYTHONHASHSEED to the salt")
    ap.add_argument("--json", metavar="OUT", help="write the full report here")
    a = ap.parse_args(argv)
    if a.all:
        names = [n for n, _, _ in oracle.SCENARIOS]
    else:
        names = [n for n in a.scenarios.split(",") if n] or [n for n, _, inf in oracle.SCENARIOS if inf]
    for n in names:
        if n not in oracle.SC_BY_NAME:
            ap.error("unknown scenario %s" % n)
    salts = [int(x) for x in a.salts.split(",") if x]
    if len(salts) < 2:
        ap.error("need at least two salts")
    report = check(a.repo, names, salts, a.jobs, a.vary_hashseed)
    print("%-28s %-7s %-8s %s" % ("scenario", "order", "outcome", "first order difference"))
    for n in names:
        e = report[n]
        where = ""
        d = e.get("first_order_difference")
        if d:
            where = "salt %s, group #%d (%s, t=%s)" % (d["salt"], d["group"], d["engine"], d["instant"])
        print("%-28s %-7s %-8s %s%s" % (n, "stable" if e["order_stable"] else "varies",
                                        "stable" if e["outcome_stable"] else "varies", where,
                                        "  ERROR: " + "; ".join(e["errors"]) if e["errors"] else ""))
    if a.json:
        with open(a.json, "w", encoding="utf-8", newline="\n") as f:
            json.dump({"repo": os.path.abspath(a.repo), "salts": salts, "vary_hashseed": a.vary_hashseed,
                       "scenarios": report}, f, indent=1)
            f.write("\n")
    return 1 if any(report[n]["errors"] for n in names) else 0


if __name__ == "__main__":
    raise SystemExit(main())
