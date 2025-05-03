import math

class CommandControlObject:
	def __init__(self, evation_heading, decoy_deployment_range):
		self.evation_heading = evation_heading
		self.deployment_range = decoy_deployment_range
		self.prev_target = None

	def get_evasion_heading(self):
		return self.evation_heading

	def threat_evaluation(self, ref_obj, target_obj):
		sx, sy, sz = ref_obj.get_position()
		tx, ty, tz = target_obj.get_position()

		print( math.sqrt((sx-tx)**2 + (sy-ty)**2 + (sz-tz)**2), self.deployment_range)

		if math.sqrt((sx-tx)**2 + (sy-ty)**2 + (sz-tz)**2) <= self.deployment_range:
			return True
		else:
			return False
	
	
	def get_target(self, ref_obj, target):
		if not self.prev_target:
			self.prev_target = target

		sx, sy, sz = ref_obj.get_position()
		tx, ty, tz = target.get_position()
		px, py, pz = self.prev_target.get_position()

		new_dist = math.sqrt((sx-tx)**2 + (sy-ty)**2 + (sz-tz)**2)
		prev_dist = math.sqrt((sx-tx)**2 + (sy-ty)**2 + (sz-tz)**2)
		
		if prev_dist > new_dist:
			self.prev_target = target

		return self.prev_target.get_position()