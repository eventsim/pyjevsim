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

class TerminationManager:
    _executors = []

    def __init__(self, executor=None):
        if executor:
            TerminationManager._executors.append(executor)
        TerminationManager.__set_terminate_handler()

    @staticmethod
    def register_executor(executor):
        """Register a SysExecutor for graceful shutdown on signal."""
        TerminationManager._executors.append(executor)

    @staticmethod
    def __set_terminate_handler():
        signal.signal(signal.SIGTERM, TerminationManager.signal_handler)
        signal.signal(signal.SIGINT, TerminationManager.signal_handler)

    @staticmethod
    def signal_handler(sig, frame):
        print(f"{datetime.datetime.now()} Signal {sig} received, terminating simulation gracefully")
        for executor in TerminationManager._executors:
            executor.terminate_simulation()
        TerminationManager._executors.clear()
