#!/usr/bin/env python
# 
# A library that provides a Modeling & Simulation Environment for Discrete Event System Formalism
#
# MIT License
# Copyright (C) 2020-2022
# Changbeom Choi <me@cbchoi.info>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""A library that provides a Modeling & Simulation Environment for Discrete Event System Formalism"""

__author__ = "me@cbchoi.info"

__all__ = [ 'behavior_model', 
			'behavior_model_executor', 
			'default_message_catcher', 
			'definition',
			'structural_model',
			'system_executor', 
			'system_message', 
			'system_object', 
			'system_simulator', 
			'termination_manager']

from .system_simulator import SystemSimulator
from .behavior_model_executor import BehaviorModelExecutor
from .system_message import SysMessage
from .definition import (
	Infinite,
	AttributeType,
	SimulationMode,
	ModelType,
	CoreModel,
	SingletonType,
	)