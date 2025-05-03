import math

class TorpedoControlObject:
	def __init__(self, range):
		self.prev_target = None
		self.range = range
		pass

	def reset_target(self):
		self.prev_target = None

	def get_target(self, ref_obj, target):
		
		if not self.prev_target:
			self.prev_target = target

		sx, sy, sz = ref_obj.get_position()
		tx, ty, tz = target.get_position()
		px, py, pz = self.prev_target.get_position()

		new_dist = math.sqrt((sx-tx)**2 + (sy-ty)**2 + (sz-tz)**2)
		prev_dist = math.sqrt((sx-px)**2 + (sy-py)**2 + (sz-pz)**2)
		
		#print("p", self.prev_target.get_position(), prev_dist)
		#print("n", target.get_position(), new_dist)

		if prev_dist > new_dist:
			self.prev_target = target

		return self.prev_target.get_position()