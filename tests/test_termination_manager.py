"""TerminationManager: handlers installed only when missing, weak registry.

Every ``simulate()`` used to call ``signal.signal`` twice and append its
executor to a module-level list that was only emptied by a signal, and
``simulate()`` on a worker thread raised ValueError from ``signal.signal``.
"""

import gc
import signal
import threading
import time
import weakref
from unittest import mock

import pytest

from pyjevsim.definition import ExecutionType, Infinite
from pyjevsim.system_executor import SysExecutor
from pyjevsim.termination_manager import TerminationManager


@pytest.fixture
def fresh_handlers():
    """Start from Python's default SIGINT/SIGTERM handlers, and put the
    process's handlers back afterwards."""
    saved = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    signal.signal(signal.SIGINT, signal.default_int_handler)
    signal.signal(signal.SIGTERM, signal.SIG_DFL)
    yield
    for sig, handler in saved.items():
        signal.signal(sig, handler)


def _executor():
    return SysExecutor(1, ex_mode=ExecutionType.V_TIME, snapshot_manager=None)


def test_repeated_simulate_registers_executor_once():
    se = _executor()
    for _ in range(5):
        se.simulate(1)
    assert sum(1 for ex in TerminationManager._executors if ex is se) == 1


def test_finished_executors_are_released():
    refs = []
    for _ in range(20):
        se = _executor()
        se.simulate(1)
        refs.append(weakref.ref(se))
    del se
    gc.collect()

    assert all(ref() is None for ref in refs)
    assert not any(ref() in TerminationManager._executors for ref in refs)


def test_handlers_installed_once(fresh_handlers):
    with mock.patch("pyjevsim.termination_manager.signal.signal",
                    wraps=signal.signal) as set_handler:
        for _ in range(3):
            _executor().simulate(1)
            TerminationManager()

    assert sorted(c.args[0] for c in set_handler.call_args_list) == sorted(
        [signal.SIGINT, signal.SIGTERM])
    assert signal.getsignal(signal.SIGINT) is TerminationManager.signal_handler
    assert signal.getsignal(signal.SIGTERM) is TerminationManager.signal_handler


def test_simulate_on_worker_thread_does_not_raise(fresh_handlers):
    errors = []
    se = _executor()

    def run():
        try:
            se.simulate(3)
        except Exception as exc:  # pragma: no cover - the failure being tested
            errors.append(exc)

    worker = threading.Thread(target=run)
    worker.start()
    worker.join(10)

    assert not worker.is_alive()
    assert errors == []
    assert se.get_global_time() == 3
    # The worker registers its executor but cannot install the handlers.
    assert se in TerminationManager._executors
    assert signal.getsignal(signal.SIGINT) is signal.default_int_handler


@pytest.mark.parametrize("sig", [signal.SIGINT, signal.SIGTERM])
def test_signal_terminates_running_simulation(fresh_handlers, sig):
    TerminationManager()  # main thread installs the handlers
    assert signal.getsignal(sig) == TerminationManager.signal_handler

    se = SysExecutor(0.01, ex_mode=ExecutionType.R_TIME, snapshot_manager=None)
    worker = threading.Thread(target=se.simulate, kwargs={"_time": Infinite})
    worker.start()
    deadline = time.monotonic() + 5
    while se.get_global_time() == 0 and time.monotonic() < deadline:
        time.sleep(0.01)

    signal.raise_signal(sig)
    worker.join(5)

    assert not worker.is_alive()
    assert se.is_terminated()


def test_handler_reinstalled_after_reset(fresh_handlers):
    """ipykernel puts default_int_handler back before every cell; the next
    main-thread simulate() must still end gracefully on SIGINT."""
    for _ in range(2):
        signal.signal(signal.SIGINT, signal.default_int_handler)
        se = SysExecutor(0.01, ex_mode=ExecutionType.R_TIME, snapshot_manager=None)
        timer = threading.Timer(0.3, signal.raise_signal, args=(signal.SIGINT,))
        timer.start()
        try:
            se.simulate(Infinite)
        except KeyboardInterrupt:
            pytest.fail("SIGINT escaped simulate() instead of terminating it")
        finally:
            timer.cancel()

        assert se.is_terminated()
