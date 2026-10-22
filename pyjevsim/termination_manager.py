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

    The handlers are installed once per process, from the main thread (Python
    only allows that thread to set them). Executors registered from another
    thread are still terminated when a signal arrives, as long as the main
    thread has installed the handlers. Executors are held weakly, so a
    finished executor that is no longer referenced is released.
    """
    _executors = weakref.WeakSet()
    _handler_installed = False

    def __init__(self, executor=None):
        if executor:
            TerminationManager._executors.add(executor)
        TerminationManager.__set_terminate_handler()

    @staticmethod
    def register_executor(executor):
        """Register a SysExecutor for graceful shutdown on signal."""
        TerminationManager._executors.add(executor)

    @staticmethod
    def __set_terminate_handler():
        if TerminationManager._handler_installed:
            return
        if threading.current_thread() is not threading.main_thread():
            return
        signal.signal(signal.SIGTERM, TerminationManager.signal_handler)
        signal.signal(signal.SIGINT, TerminationManager.signal_handler)
        TerminationManager._handler_installed = True

    @staticmethod
    def signal_handler(sig, frame):
        print(f"{datetime.datetime.now()} Signal {sig} received, terminating simulation gracefully")
        for executor in list(TerminationManager._executors):
            executor.terminate_simulation()
        TerminationManager._executors.clear()
