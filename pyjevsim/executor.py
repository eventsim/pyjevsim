'''
 Author: Changbeom Choi (@cbchoi)
 Copyright (c) 2014-2020 Handong Global University
 Copyright (c) 2014-2020 Hanbat National University
 License: MIT.  The full license text is available at:
  - https://github.com/eventsim/pyjevsim/blob/main/LICENSE
'''

class Executor:
	def __init__(self, itime, dtime, ename):
		self.engine_name = ename
		self._instance_t = itime
		self._destruct_t = dtime
