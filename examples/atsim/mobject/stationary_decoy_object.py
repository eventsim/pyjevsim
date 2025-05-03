import math

class StationaryDecoyObject:
	def __init__(self, pos, decoy_info):
		self.x, self.y, self.z = pos
		self.g = 9.8
		self.elevation = decoy_info['elevation']
		self.azimuth   = decoy_info['azimuth']
		self.speed     = decoy_info['speed']
		self.z_speed   = decoy_info['speed']
		self.lifespan  = decoy_info['lifespan']
		self.active    = True

	def get_position(self):
		return (self.x, self.y, self.z)

	def check_lifespan(self, dt):
		self.lifespan -= dt
		if self.lifespan < 0:
			self.active = False
			return False
		else:
			self.active = True
			return True

	def check_active(self):
		return self.active

	def calc_next_pos(self, dt):
		 # Convert degrees ¡æ radians
		theta = math.radians(self.elevation)
		phi   = math.radians(self.azimuth)
		    
		vx0 = self.speed * math.cos(theta) * math.sin(phi)
		vy0 = self.speed * math.cos(theta) * math.cos(phi)
		vz0 = self.z_speed * math.sin(theta)

		self.x = self.x + vx0 * dt
		self.y = self.y + vy0 * dt
		self.z = self.z + vz0 * dt - 0.5 * self.g * dt**2
		
		if self.z < 0:
			self.z = 0

		self.z_speed -= self.g * dt