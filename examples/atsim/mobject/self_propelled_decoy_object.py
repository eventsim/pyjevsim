import math

class SelfPropelledDecoyObject:
	def __init__(self, pos, tof, decoy_info):
		self.x, self.y, self.z = pos
		self.g = 9.8
		self.time_of_flight		= tof
		self.elevation			= decoy_info['elevation']
		self.azimuth			= decoy_info['azimuth']
		self.launch_speed		= decoy_info['speed']
		self.z_speed			= decoy_info['speed']
		self.lifespan			= decoy_info['lifespan']
		self.heading			= decoy_info['heading']
		self.xy_speed			= decoy_info['xy_speed']
		self.active				= True
		self.propelled_mode		= False

	def get_position(self):
		return (self.x, self.y, self.z)

	def check_flight(self, dt):
		self.time_of_flight -= dt
		if self.time_of_flight < 0:
			return False
		else:
			return True

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
		if not self.propelled_mode :
			 # Convert degrees to radians
			theta = math.radians(self.elevation)
			phi   = math.radians(self.azimuth)
		    
			vx0 = self.launch_speed * math.cos(theta) * math.sin(phi)
			vy0 = self.launch_speed * math.cos(theta) * math.cos(phi)
			vz0 = self.z_speed * math.sin(theta)

			self.x = self.x + vx0 * dt
			self.y = self.y + vy0 * dt
			self.z = self.z + vz0 * dt - 0.5 * self.g * dt**2
		
			if self.z < 0:
				self.z = 0
				self.propelled_mode = True

			if self.z_speed >= 0:
				self.z_speed -= self.g * dt
		else:
			self.calc_next_pos_with_heading(dt)

	def calc_next_pos_with_heading(self, dt):
		#print("h", self.x, self.y, self.z)
		# Convert heading from degrees to radians
		heading_radians = math.radians(self.heading)

		# Calculate x and y positions
		# In this coordinate system: x is based on sin, y is based on cos
		self.x += dt * self.xy_speed * math.sin(heading_radians)
		self.y += dt * self.xy_speed * math.cos(heading_radians)