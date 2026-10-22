"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

Tests for the standard performance suite harness (benchmark/suite.py).

Only the bookkeeping is tested here (parity refusal, ratio statistics, CPU
set parsing) plus one tiny end-to-end run; the timings themselves are not.
"""

import json
import os
import sys

import pytest

from benchmark import suite
from benchmark.workloads import DEFAULT_WORKLOADS, WORKLOADS, resolve

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run(parity, sim_s):
    return {"parity": parity, "metrics": {"sim_s": sim_s}}


def test_registry_lists_w1_to_w7():
    assert DEFAULT_WORKLOADS == ("W1", "W2", "W3", "W4", "W5", "W6", "W7")
    assert set(WORKLOADS) == set(DEFAULT_WORKLOADS)
    assert resolve("w3").wid == "W3"
    with pytest.raises(ValueError):
        resolve("W9")


def test_child_checks_where_pyjevsim_and_examples_come_from(tmp_path):
    import types

    import examples
    import pyjevsim
    from benchmark.workloads import child

    assert [w for w in WORKLOADS.values() if w.uses_examples] == [
        WORKLOADS["W5"]]
    assert child._check_origin(pyjevsim, REPO) == os.path.abspath(
        pyjevsim.__file__)
    assert child._check_origin(examples, REPO).startswith(REPO)
    stray = types.ModuleType("examples")
    stray.__file__ = str(tmp_path / "examples" / "__init__.py")
    with pytest.raises(SystemExit, match="examples resolved to"):
        child._check_origin(stray, REPO)


def test_parity_must_match_within_and_across_sides():
    ok, _, key = suite.check_parity({
        "base": [_run({"t": 5}, 1.0), _run({"t": 5}, 1.1)],
        "cand": [_run({"t": 5}, 0.9)],
    })
    assert ok and key == {"t": 5}

    ok, reason, _ = suite.check_parity({
        "base": [_run({"t": 5}, 1.0)], "cand": [_run({"t": 6}, 0.5)]})
    assert not ok and "differ" in reason

    ok, reason, _ = suite.check_parity({
        "base": [_run({"t": 5}, 1.0), _run({"t": 4}, 1.0)]})
    assert not ok and "base runs disagree" in reason


def test_compare_metric_uses_ratio_of_minimums_and_paired_median():
    base = [1.00, 1.10, 1.05]
    cand = [0.80, 0.95, 0.84]
    s = suite.compare_metric(base, cand, floor=0.05)
    assert s["ratio_of_min"] == pytest.approx(0.80)
    assert s["median_ratio"] == pytest.approx(0.80)
    assert s["ratio_spread"] == pytest.approx([0.8, 0.8636], abs=1e-3)
    assert s["verdict"] == "faster"
    # Inside the noise floor nothing is claimed.
    assert suite.compare_metric([1.0, 1.0], [1.03, 0.99])["verdict"] == "noise"
    # Min and median disagree in direction: no claim either.
    assert suite.verdict(0.90, 1.02, 0.05) == "unclear"


@pytest.mark.parametrize("text,cpus", [
    ("0-3", [0, 1, 2, 3]),
    ("0,2,4-5", [0, 2, 4, 5]),
    ("0xF0", [4, 5, 6, 7]),
    ("5", [0, 2]),
])
def test_parse_cpu_set(text, cpus):
    assert suite.parse_cpu_set(text) == cpus


def test_parse_cpu_set_rejects_empty_sets():
    with pytest.raises(ValueError):
        suite.parse_cpu_set("0x0")
    with pytest.raises(ValueError):
        suite.parse_cpu_set("3-1")


def test_parse_cpu_set_rejects_out_of_range_indices():
    assert suite.parse_cpu_set("0-3", limit=4) == [0, 1, 2, 3]
    with pytest.raises(ValueError, match="CPU index 4 is out of range"):
        suite.parse_cpu_set("0-4", limit=4)
    # CPU 64 does not fit a 64-bit Windows affinity mask; it used to be
    # truncated away silently, pinning to CPU 1 alone.
    with pytest.raises(ValueError, match="CPU index 64"):
        suite.parse_cpu_set("0x10000000000000002", limit=64)
    with pytest.raises(ValueError):
        suite.parse_cpu_set("0-99", limit=8)


def test_cpu_limit_matches_the_platform():
    limit = suite.cpu_limit()
    assert 1 <= limit <= (os.cpu_count() or 1)
    if sys.platform == "win32":
        assert limit <= 64


def test_set_affinity_rejects_an_out_of_range_cpu_before_pinning():
    # Raised before any platform call, so this process is not pinned.
    with pytest.raises(ValueError):
        suite.set_affinity([0, suite.cpu_limit()])


def test_main_rejects_an_out_of_range_pin(capsys):
    bad = str(suite.cpu_limit())
    assert suite.main(["--pin", f"0,{bad}", "--workloads", "W3"]) == 2
    assert f"CPU index {bad} is out of range" in capsys.readouterr().err
    assert suite.main(["--pin", "0x10000000000000002"]) == 2


@pytest.mark.parametrize("exc", [OSError(87, "The parameter is incorrect"),
                                 NotImplementedError("no affinity API")])
def test_main_reports_a_failed_pin_without_a_traceback(monkeypatch, capsys,
                                                       exc):
    def fail(cpus, process=None):
        raise exc

    def never(*args, **kwargs):
        raise AssertionError("the suite ran after a failed pin")

    monkeypatch.setattr(suite, "set_affinity", fail)
    monkeypatch.setattr(suite, "run_suite", never)
    assert suite.main(["--pin", "0x1", "--workloads", "W3"]) == 2
    assert "error: cannot pin to 0x1" in capsys.readouterr().err


def test_param_overrides_are_parsed_per_workload():
    assert suite._parse_params(["W3.count=200", "w1.variant=LI"]) == {
        "W3": {"count": 200}, "W1": {"variant": "LI"}}
    with pytest.raises(ValueError):
        suite._parse_params(["count=200"])


def _fake_run_once(fail):
    """A run_once stand-in: ``fail`` is {(wid, side_path): call_number}."""
    calls = {}

    def run_once(wid, repo, python=None, params=None, cpus=None,
                 timeout=None):
        n = calls[wid, repo] = calls.get((wid, repo), 0) + 1
        if fail.get((wid, repo)) == n:
            raise suite.ChildError(f"{wid} on {repo}: exit 1 | no result\n"
                                   "Traceback (most recent call last)")
        parity = {"t": 7} if not (wid == "W2" and repo == "c") else {"t": 8}
        return {"parity": parity, "metrics": {"sim_s": 1.0}}

    return run_once


def test_a_failed_child_drops_only_its_workload(monkeypatch, capsys):
    # W1's candidate fails on its third call (warm-up, round 1, then round
    # 2, which runs the candidate first); W2 is refused; W3 is fine.
    monkeypatch.setattr(suite, "run_once", _fake_run_once({("W1", "c"): 3}))
    doc = suite.run_suite({"base": "b", "cand": "c"}, ["W1", "W2", "W3"],
                          rounds=3, warmup=1, quiet=True)
    w1, w2, w3 = (doc["workloads"][w] for w in ("W1", "W2", "W3"))
    assert doc["status"] == 1
    assert w1["failed"].startswith("cand: W1 on c") and not w1["parity_ok"]
    # Round 1's runs are kept; nothing of W1 runs after the failure.
    assert len(w1["runs"]["base"]) == 1 and len(w1["runs"]["cand"]) == 1
    assert w2["failed"] is None and "differ" in w2["refused"]
    assert w3["parity_ok"] and w3["summary"]["sim_s"]["verdict"] == "noise"
    assert len(w3["runs"]["cand"]) == 3
    assert "W1 failed" in capsys.readouterr().err

    rows = suite.format_report(doc, markdown=True).splitlines()
    table = [r for r in rows if r.startswith("| W")]
    # Every row has the header's 8 cells (9 separators; the escaped pipe in
    # the FAILED reason does not count).
    assert [r.replace(r"\|", "").count("|") for r in table] == [9, 9, 9]
    assert table[0].endswith("| FAILED |") and "Traceback" not in table[0]
    assert table[1].endswith("| REFUSED |")
    assert "FAILED: cand: W1" in suite.format_report(doc)


def test_main_writes_out_when_a_workload_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(suite, "run_once", _fake_run_once(
        {("W1", REPO): 1}))
    out = tmp_path / "r.json"
    assert suite.main(["--workloads", "W1,W3", "--rounds", "2", "--quiet",
                       "--out", str(out)]) == 1
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["workloads"]["W1"]["failed"]
    assert doc["workloads"]["W3"]["parity_ok"]


def test_single_checkout_run_end_to_end():
    # One fresh child process per run; tiny W3 so this stays fast.
    doc = suite.run_suite({"repo": REPO}, ["W3"], rounds=2, warmup=0,
                          params={"W3": {"count": 50}}, quiet=True)
    entry = doc["workloads"]["W3"]
    assert doc["status"] == 0 and entry["parity_ok"]
    assert entry["parity"] == {"fired": 50, "received": 50,
                               "global_time": 504}
    assert entry["summary"]["sim_s"]["n"] == 2
    assert all(r["pyjevsim_file"].startswith(REPO)
               for r in entry["runs"]["repo"])
