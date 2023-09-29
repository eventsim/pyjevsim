from behavior_model_executor import BehaviorModelExecutor
from definition import ModelType

class ExecutorFactory:
	def __init__(self):
		pass

	def create_executor(self, ins_t, des_t, en_name, model):
		if model.get_model_type() == ModelType.BEHAVIORAL:
			return BehaviorModelExecutor(ins_t, des_t, en_name, model)