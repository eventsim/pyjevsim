"""
Author: Changbeom Choi (@cbchoi)
Copyright (c) 2014-2020 Handong Global University
Copyright (c) 2021-2024 Hanbat National University
License: MIT.  The full license text is available at:
https://github.com/eventsim/pyjevsim/blob/main/LICENSE

This module contains a BehaivorModel object that allows you to implement the Discrete Event System Specification AtomicModel. 
"""

from abc import abstractmethod
from collections import OrderedDict

from .behavior_model import BehaviorModel
from .definition import ModelType

class AtomicModel(BehaviorModel):
	def __init__(self, _name=""):
		super().__init__(_name)

	@abstractmethod
	def ext_trans(self, port, msg):
		"""Defines the external transition, to be implemented by subclasses"""
		pass

	@abstractmethod
	def int_trans(self):
		"""Defines the internal transition, to be implemented by subclasses"""
		pass

	@abstractmethod
	def output(self):
		"""Defines the output function, to be implemented by subclasses"""
		pass

	@abstractmethod
	def time_advance(self):
		"""Defines the output function, to be implemented by subclasses"""
		return -1