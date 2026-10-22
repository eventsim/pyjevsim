"""Smoke tests for the trace oracle in ``tools/oracle``.

The fast test runs one small verdict scenario through the command line in
hash mode and checks its sha256 against the current golden. The full run
takes about a minute and is skipped unless ``PYJEVSIM_ORACLE_FULL=1``.
"""

import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORACLE_DIR = os.path.join(ROOT, "tools", "oracle")
ORACLE = os.path.join(ORACLE_DIR, "trace_oracle.py")


def _current_golden():
    sys.path.insert(0, ORACLE_DIR)
    try:
        import trace_oracle
    finally:
        sys.path.remove(ORACLE_DIR)
    with open(trace_oracle.GOLDEN, encoding="utf-8") as f:
        return json.load(f)


def _oracle(*args, timeout=60):
    return subprocess.run(
        [sys.executable, ORACLE, "--repo", ROOT, *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=timeout,
    )


def test_confluent_scenario_hash_matches_golden(tmp_path):
    out = tmp_path / "hashes.json"
    p = _oracle("--scenarios", "tests_confluent", "--hash-only", "--out", str(out))
    assert p.returncode == 0, p.stdout + p.stderr

    got = json.loads(out.read_text(encoding="utf-8"))
    golden = _current_golden()
    entry = got["scenarios"]["tests_confluent"]
    assert entry["error"] is None
    assert entry["sha256"] == golden["scenarios"]["tests_confluent"]["sha256"]
    assert "tests_confluent" not in got["skipped"]
    assert set(got["skipped"]) | {"tests_confluent"} == set(golden["scenarios"])


def test_compare_reports_a_changed_hash(tmp_path):
    golden = _current_golden()
    changed = dict(golden, scenarios={
        "tests_confluent": dict(golden["scenarios"]["tests_confluent"], sha256="0" * 64),
    })
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    a.write_text(json.dumps(golden), encoding="utf-8")
    b.write_text(json.dumps(changed), encoding="utf-8")

    p = _oracle("--compare", str(a), str(b))
    assert p.returncode == 1
    assert "DIFF  tests_confluent" in p.stdout
    assert "SKIPPED   bank_canon" not in p.stdout   # absent but not marked skipped
    assert "MISSING   bank_canon" in p.stdout


@pytest.mark.skipif(os.environ.get("PYJEVSIM_ORACLE_FULL") != "1",
                    reason="full oracle run; set PYJEVSIM_ORACLE_FULL=1")
def test_full_run_matches_golden():
    p = _oracle("--golden", timeout=1800)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "RESULT: PASS" in p.stdout
