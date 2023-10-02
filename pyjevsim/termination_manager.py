'''
 Author: Changbeom Choi (@cbchoi)
 Copyright (c) 2014-2020 Handong Global University
 Copyright (c) 2014-2020 Hanbat National University
 License: MIT.  The full license text is available at:
  - https://github.com/eventsim/pyjevsim/blob/main/LICENSE
'''

import signal
import os
import datetime

class TerminationManager:
    def __init__(self):
        TerminationManager.__set_terminate_handler()

    @staticmethod
    def __set_terminate_handler():
        signal.signal(signal.SIGTERM, TerminationManager.__handler)
        signal.signal(signal.SIGINT,  TerminationManager.__handler)

    @staticmethod
    def __handler(sig, frame):
        try:
            print(f"{datetime.datetime.now()} Simulation Engine Terminated Gracefully")
        except Exception as e:
            print(e)
            raise
        finally:
            os._exit(0)
