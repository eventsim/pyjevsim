import math

class Detector:
	def __init__(self, detect_range):
		self.detect_range = detect_range

	def detect(self, ref_pos, target_pos):
		sx, sy, sz = self.ref_pos
		tx, ty, tz = self.target_pos

		if math.sqrt((sx-tx)**2, (sy-ty)**2, (sz-tz)**2) <= detect_range:
			return True
		else:
			return False