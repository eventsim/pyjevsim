"""
 Author: Changbeom Choi (@cbchoi)
 Copyright (c) 2014-2020 Handong Global University
 Copyright (c) 2014-2020 Hanbat National University
 License: MIT.  The full license text is available at:
  - https://github.com/eventsim/pyjevsim/blob/main/LICENSE
"""

import datetime
import os
import signal


class TerminationManager:
    def __init__(self):
        TerminationManager.__set_terminate_handler()

    @staticmethod
    def __set_terminate_handler():
        signal.signal(signal.SIGTERM, TerminationManager.signal_handler)
        signal.signal(signal.SIGINT, TerminationManager.signal_handler)

    @staticmethod
    def signal_handler(sig, frame):
        try:
            print(sig, frame)
            print(f"{datetime.datetime.now()} Simulation Engine Terminated Gracefully")
        except Exception as exception:
            print(exception)
            raise
        finally:
            os._exit(0)
