from .behavior_model_executor import BehaviorModelExecutor
from .structural_executor import StructuralExecutor
from .definition import ModelType

class ExecutorFactory:
	def __init__(self):
		pass

	def create_executor(self, global_time, ins_t, des_t, en_name, model, ):
		if model.get_model_type() == ModelType.BEHAVIORAL:
			return self.create_behavior_executor(global_time, ins_t, des_t, en_name, model)
		if model.get_model_type() == ModelType.STRUCTURAL:
			return self.create_structural_executor(global_time, ins_t, des_t, en_name, model)

	def create_behavior_executor(self, global_time, ins_t, des_t, en_name, model):
		return BehaviorModelExecutor(ins_t, des_t, en_name, model)

	def create_structural_executor(self, global_time, ins_t, des_t, en_name, model):
		return StructuralExecutor(global_time, ins_t, des_t, en_name, model, self.create_behavior_executor)