import signal
import os
import datetime

class TerminationManager(object):
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
			raise
		finally:
			os._exit(0)