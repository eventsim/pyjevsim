"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

This module contains the TerminatorManager, which manages the simulation termination of the SysExecutor. 
"""

import datetime
import signal
import threading
import weakref

class TerminationManager:
    """Terminates registered SysExecutors on SIGINT or SIGTERM.

    The handlers are installed from the main thread (Python only allows that
    thread to set them), and only when they are not already in place, so
    repeated runs do not call ``signal.signal`` again but a handler that was
    reset in between (ipykernel resets SIGINT before every cell) is installed
    again. Executors registered from another thread are still terminated
    when a signal arrives, as long as the main thread has installed the
    handlers. Executors are held weakly, so a finished executor that is no
    longer referenced is released.
    """
    _executors = weakref.WeakSet()

    def __init__(self, executor=None):
        if executor:
            TerminationManager._executors.add(executor)
        TerminationManager.install_handlers()

    @staticmethod
    def register_executor(executor):
        """Register a SysExecutor for graceful shutdown on signal."""
        TerminationManager._executors.add(executor)

    @staticmethod
    def attach(executor):
        """Register ``executor`` and make sure the handlers are installed.

        ``SysExecutor.simulate()`` calls this on every run, so it does what
        the constructor does without building a ``TerminationManager``.
        Registering an executor that is already registered is a no-op.
        """
        TerminationManager._executors.add(executor)
        TerminationManager.install_handlers()

    @staticmethod
    def install_handlers():
        """Install the SIGTERM/SIGINT handlers if they are not in place.

        Does nothing off the main thread, where Python does not allow it.
        """
        if threading.current_thread() is not threading.main_thread():
            return
        for sig in (signal.SIGTERM, signal.SIGINT):
            if signal.getsignal(sig) is not TerminationManager.signal_handler:
                signal.signal(sig, TerminationManager.signal_handler)

    @staticmethod
    def signal_handler(sig, frame):
        print(f"{datetime.datetime.now()} Signal {sig} received, terminating simulation gracefully")
        for executor in list(TerminationManager._executors):
            executor.terminate_simulation()
        TerminationManager._executors.clear()
