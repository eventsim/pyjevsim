"""Regression tests for the strict live-RTI validation wrapper."""

from __future__ import annotations

import importlib.util
import io
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest


def _load_live_verifier():
    path = (
        Path(__file__).resolve().parents[2]
        / "examples"
        / "hla_atsim"
        / "verify_equivalence_rti.py"
    )
    spec = importlib.util.spec_from_file_location("_live_verifier_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_example_script(relative_path: str, module_name: str):
    path = Path(__file__).resolve().parents[2] / relative_path
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_nonzero_live_process_cannot_pass_with_a_valid_looking_trace(
    monkeypatch,
):
    verifier = _load_live_verifier()
    verifier.RTI = "fake"

    def failed_run(*args, **kwargs):
        return SimpleNamespace(returncode=7, stdout="partial", stderr="failed")

    monkeypatch.setattr(verifier.os.path, "exists", lambda path: True)
    monkeypatch.setattr(verifier.os, "remove", lambda path: None)
    monkeypatch.setattr(
        "builtins.open",
        lambda *args, **kwargs: io.StringIO(
            "tick,object_name,x,y,z\n1,obj,0,0,0\n"
        ),
    )
    monkeypatch.setattr(verifier.subprocess, "run", failed_run)
    assert verifier._rti_rows("case") is None


def test_live_trace_header_is_validated(monkeypatch):
    verifier = _load_live_verifier()
    verifier.RTI = "fake"

    def successful_run(*args, **kwargs):
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(verifier.os.path, "exists", lambda path: True)
    monkeypatch.setattr(verifier.os, "remove", lambda path: None)
    monkeypatch.setattr(
        "builtins.open",
        lambda *args, **kwargs: io.StringIO("wrong,header\n1,obj,0,0,0\n"),
    )
    monkeypatch.setattr(verifier.subprocess, "run", successful_run)
    assert verifier._rti_rows("case") is None


def test_live_process_timeout_is_a_validation_failure(monkeypatch):
    verifier = _load_live_verifier()
    verifier.RTI = "fake"
    verifier.LIVE_TIMEOUT = 0.01

    def timed_out(command, **kwargs):
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(verifier.os.path, "exists", lambda path: False)
    monkeypatch.setattr(verifier.subprocess, "run", timed_out)
    assert verifier._rti_rows("case") is None


def test_portico_validation_uses_portico_wrapper(monkeypatch):
    verifier = _load_live_verifier()
    verifier.RTI = "portico"
    invoked = {}

    def successful_run(command, **kwargs):
        invoked["command"] = command
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(verifier.os.path, "exists", lambda path: True)
    monkeypatch.setattr(verifier.os, "remove", lambda path: None)
    monkeypatch.setattr(
        "builtins.open",
        lambda *args, **kwargs: io.StringIO(
            "tick,object_name,x,y,z\n1,obj,0,0,0\n"
        ),
    )
    monkeypatch.setattr(verifier.subprocess, "run", successful_run)

    assert verifier._rti_rows("case") == [("1", "obj", "0", "0", "0")]
    assert Path(invoked["command"][1]).name == "run_hla_portico.py"


def test_portico_wrapper_uses_bundled_same_jvm_rid(monkeypatch):
    monkeypatch.delenv("RTI_RID_FILE", raising=False)
    wrapper = _load_example_script(
        "examples/hla_atsim/run_hla_portico.py",
        "_atsim_portico_wrapper_default_test",
    )

    assert Path(os.environ["RTI_RID_FILE"]) == wrapper.DEFAULT_RID
    assert wrapper.DEFAULT_RID.is_file()
    assert "portico.connection = jvm" in wrapper.DEFAULT_RID.read_text(
        encoding="utf-8"
    )


def test_portico_wrapper_preserves_user_rid(monkeypatch):
    custom_rid = Path("D:/custom-portico.rid")
    monkeypatch.setenv("RTI_RID_FILE", str(custom_rid))
    _load_example_script(
        "examples/hla_atsim/run_hla_portico.py",
        "_atsim_portico_wrapper_override_test",
    )

    assert os.environ["RTI_RID_FILE"] == str(custom_rid)


def test_live_runner_rejects_missing_peer_and_propagates_worker_error():
    runner = _load_example_script(
        "examples/hla_atsim/run_hla_pitch.py",
        "_atsim_live_runner_helpers_test",
    )

    with pytest.raises(RuntimeError, match="expected peer 'peer'"):
        runner._require_peer_reflection("ship", {}, "peer")

    cause = ValueError("worker failed")
    with pytest.raises(RuntimeError, match="ship live-RTI worker failed") as raised:
        runner._raise_worker_errors([("ship", cause)])
    assert raised.value.__cause__ is cause
