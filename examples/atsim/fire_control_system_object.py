import math

class FireControlSystemObject:
	def __init__(self, decoy_deployment_range):
		self.deployment_range = decoy_deployment_range

	def threat_evaluation(self, ref_obj, target_obj):
		sx, sy, sz = ref_obj.get_position()
		tx, ty, tz = target_obj.get_position()

		print( math.sqrt((sx-tx)**2 + (sy-ty)**2 + (sz-tz)**2), self.deployment_range)

		if math.sqrt((sx-tx)**2 + (sy-ty)**2 + (sz-tz)**2) <= self.deployment_range:
			return True
		else:
			return False