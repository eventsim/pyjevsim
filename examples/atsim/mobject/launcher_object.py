import math

class LauncherObject:
	def __init__(self, DecoyObjects):
		self.decoy_list = DecoyObjects

		print(self.decoy_list)

	def get_decoy_count(self):
		return len(self.decoy_list)

	def get_time_of_flight(self, decoy, init_height= 0, g = 9.8):
		speed = decoy['speed'] 
		elevation_deg = decoy['elevation']

		# Convert degrees to radians for trigonometric functions
		theta = math.radians(elevation_deg)

		# Initial vertical velocity component
		v_z0 = speed * math.sin(theta)

		# Quadratic discriminant for z(t) = 0
		discriminant = v_z0**2 + 2 * g * init_height

		# Positive root gives the physical flight time
		return (v_z0 + math.sqrt(discriminant)) / g