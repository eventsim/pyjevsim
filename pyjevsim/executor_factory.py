from behavior_model_executor import BehaviorModelExecutor

class ExecutorFactory:
	def __init__(self):
		pass

	def create_executor(self, bm, ins_t, des_t, en_name):
		return BehaviorModelExecutor(ins_t, des_t, en_name, bm)