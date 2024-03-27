import sys
from pyevsim import Infinite, SysMessage, SystemSimulator, BehaviorModelExecutor
from pyevsim.definition import Infinite
import random

class BankUser:
	def __init__(self, _id:int, s_t:float):
		self.user_id 	= _id
		self.wait_t     = 0.0
		self.done_t 	= 0.0
		self.arrival_t 	= 0.0
		self.service_t 	= s_t

	## Requirements
	# - User는 ID로 구분된다. 
	# - User의 대기시간은 은행에 도착한 순간부터 기록한다. 
	# - 사용자의 서비스 시간은 랜덤하게 결정된다. 
	def get_id(self) -> int:
		return self.user_id

	def get_wait_time(self) -> float:
		return self.wait_t

	def get_arrival_time(self) -> float:
		return self.arrival_t

	def get_service_time(self) -> float:
		return self.service_t

	def set_arrival_time(self, a_t:float) -> None:
		self.arrival_t = a_t

	def calc_wait_time(self, w_t:float) -> None:
		self.done_t = w_t
		self.wait_t = w_t - self.arrival_t


	def __str__(self):
		return f"{self.get_id()}, {self.service_t}, {self.arrival_t}, {self.done_t}, {self.wait_t}"

class BankUserGenerator(BehaviorModelExecutor):
	def __init__(self, ins_t, des_t, name, engine):
		BehaviorModelExecutor.__init__(self, ins_t, des_t, name, engine)

		self.init_state("WAIT")
		self.insert_state("WAIT", Infinite)
		self.insert_state("GEN", 1)

		self.insert_input_port("start")
		self.insert_output_port("user_out")

		self.generated_user = 0
		pass

	def ext_trans(self, port, msg):
		if port == "start":
			self._cur_state = "GEN"
		pass

	def output(self):
		_time = SystemSimulator.get_engine(self.get_engine_name()).get_global_time()
		print(f"[G] ID:{self.generated_user} Time:{_time}")
		
		msg = SysMessage(self.get_name(), "user_out")
		
		bu = BankUser(self.generated_user, 2)
		bu.set_arrival_time(_time)
		msg.insert(bu)
		
		self.generated_user += 1

		return msg

	def int_trans(self):
		if self._cur_state == "GEN" and self.generated_user >= 200: # 
			self._cur_state = "WAIT"
		else:
			self.update_state("GEN", 1)

class BankQueue(BehaviorModelExecutor):
	def __init__(self, ins_t, des_t, name, engine):
		BehaviorModelExecutor.__init__(self, ins_t, des_t, name, engine)

		self.init_state("WAIT")
		self.insert_state("WAIT", Infinite)
		self.insert_state("CHECK", 0)
		self.insert_state("READY", Infinite)
		self.insert_state("SEND", 0)

		self.insert_input_port("in")
		self.insert_input_port("next")

		self.insert_output_port("ready")
		self.insert_output_port("out")

		self.insert_state("SEND_OK", 0)
		self.insert_state("SEND_OK_AFTER", 0)
		self.insert_input_port("check")
		self.insert_output_port("ok")

		self.user = None
		pass

	def ext_trans(self, port, msg):
		_time = SystemSimulator.get_engine(self.get_engine_name()).get_global_time()
		if port == "in":
			if not self.user:
				self.user = msg.retrieve()[0]
				print(f"{self.get_name()}[in] ID:{self.user.get_id()} Time:{_time}")
			else:
				print(f"User Dropped: {msg.retrieve()[0]}")

			
			self._cur_state = "CHECK"
		elif port == "next":
			if self.user:
				print(f"{self.get_name()} Confirm Time:{_time}")
				self._cur_state = "SEND"
			else:
				self._cur_state = "SEND_OK"

		elif port == "check":
			print(f"Receive Ack {self.get_name()}")
			if self.user:
				self.cancel_rescheduling()
			else:
				self._cur_state = "SEND_OK"
				
		pass

	def output(self):
		msg = None
		_time = SystemSimulator.get_engine(self.get_engine_name()).get_global_time()
		if self._cur_state == "CHECK":
			print(f"{self.get_name()} Check")
			msg = SysMessage(self.get_name(), "ready")
		elif self._cur_state == "SEND":
			print(f"{self.get_name()}[out] ID:{self.user.get_id()} Time:{_time}")
			
			msg = SysMessage(self.get_name(), "out")
			msg.insert(self.user)
			self.user = None

		elif self._cur_state == "SEND_OK":
			print(f"SEND_OK {self.get_name()}")
			msg = SysMessage(self.get_name(), "ok")

		elif self._cur_state == "SEND_OK_AFTER":
			print(f"SEND_OK {self.get_name()}")
			msg = SysMessage(self.get_name(), "ok")

		return msg

	def int_trans(self):
		if self._cur_state == "WAIT":
			self._cur_state = "CHECK"
		elif self._cur_state == "CHECK":
			self._cur_state = "READY"

		elif self._cur_state == "SEND":
			self._cur_state = "SEND_OK_AFTER"
		elif self._cur_state == "SEND_OK":
			print(f"WAIT {self.get_name()}")
			self._cur_state = "WAIT"
		elif self._cur_state == "SEND_OK_AFTER":
			self._cur_state = "WAIT"

	def __str__(self):
		return f">> {self.get_name()}, State:{self._cur_state}, {self.user}"

class BankAccountant(BehaviorModelExecutor):
	def __init__(self, ins_t, des_t, name, engine):
		BehaviorModelExecutor.__init__(self, ins_t, des_t, name, engine)

		self.init_state("WAIT")
		self.insert_state("WAIT", Infinite)
		self.insert_state("PROC", 1)
		self.insert_state("EMPTY", 0)

		self.insert_input_port("check")
		self.insert_input_port("in")

		self.insert_output_port("next")

		self.user = None
		self.proc_user = []

	def ext_trans(self, port, msg):
		_time = SystemSimulator.get_engine(self.get_engine_name()).get_global_time()
		if port == "check":
			if self._cur_state == "WAIT":
				print("[A] WAIT")
				self._cur_state = "EMPTY"
			else:
				self.cancel_rescheduling()

		if port == "in":
			self.user = msg.retrieve()[0]
			self._cur_state = "PROC"
			self.update_state("PROC", self.user.get_service_time())
			print(f"[A][arrive] ID:{self.user.get_id()} Time:{_time}")
		pass

	def output(self):
		_time = SystemSimulator.get_engine(self.get_engine_name()).get_global_time()
		msg = None
		if self._cur_state == "PROC":
			cur_time = SystemSimulator.get_engine(self.get_engine_name()).get_global_time()
			self.user.calc_wait_time(cur_time)
			self.proc_user.append(self.user)
			print(f"[A][processed] ID:{self.user.get_id()} Time:{_time}")

			msg = SysMessage(self.get_name(), "next")

		elif self._cur_state == "EMPTY":
			print("[A] EMPTY")
			msg = SysMessage(self.get_name(), "next")			

		return msg

	def int_trans(self):
		if self._cur_state == "PROC":
			self._cur_state = "WAIT"
		elif self._cur_state == "EMPTY":
			self._cur_state = "WAIT"

	def __del__(self):
		for user in self.proc_user:
			print(user)

	def __str__(self):
		return f">> {self.get_name()}, State:{self._cur_state}, {self.user}"

ss = SystemSimulator()
engine = ss.register_engine("bank", "VIRTUAL_TIME", 1)

bq =[]

for i in range(int(sys.argv[1])):
	bqi = BankQueue(0, Infinite, f'[Q{i}]', "bank")
	bq.append(bqi)
	engine.register_entity(bqi)	

for i, v in enumerate(bq):
	if i+1 < len(bq):
		engine.coupling_relation(bq[i], 'ready', bq[i+1], 'check')
		engine.coupling_relation(bq[i], 'out', bq[i+1], 'in')
		engine.coupling_relation(bq[i+1], 'ok', bq[i], 'next') 

ba = BankAccountant(0, Infinite, 'BankAccountant', "bank")
engine.register_entity(ba)

engine.insert_input_port('start')

bug = BankUserGenerator(0, Infinite, 'BankUserGenerator', "bank")
engine.register_entity(bug)

engine.coupling_relation(None, 'start', bug, 'start')
engine.coupling_relation(bug, 'user_out', bq[0], 'in')


engine.coupling_relation(bq[-1], 'out', ba, 'in')
engine.coupling_relation(bq[-1], 'ready', ba, 'check')
engine.coupling_relation(ba, 'next', bq[-1], 'next')

engine.insert_external_event('start', None)

for i in range(100):
	engine.simulate(1)
	for q in bq:
		print(q)

	print(ba)

#engine.simulate()