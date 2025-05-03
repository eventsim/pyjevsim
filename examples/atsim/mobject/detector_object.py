import math

class DetectorObject:
	def __init__(self, detection_range):
		self.detect_range = detection_range

	def detect(self, ref_obj, target_obj):
		sx, sy, sz = ref_obj.get_position()
		tx, ty, tz = target_obj.get_position()

		print( math.sqrt((sx-tx)**2 + (sy-ty)**2 + (sz-tz)**2), self.detect_range)

		if math.sqrt((sx-tx)**2 + (sy-ty)**2 + (sz-tz)**2) <= self.detect_range:
			return True
		else:
			return False