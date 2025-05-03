import math

class ManueverObject:
	def __init__(self, x, y, z, heading, xy_speed, z_speed):
		self.x = x
		self.y = y
		self.z = z
		self.heading = heading
		self.xy_speed = xy_speed
		self.z_speed = z_speed

	def get_position(self):
		return (self.x, self.y, self.z)

	def change_z_speed(self, z_spd):
		self.z_speed = z_spd

	def change_speed(self, speed):
		self.xy_speed = speed

	def change_heading(self, heading):
		self.heading = heading

	def calc_next_pos_with_heading(self, dt):
		print("h", self.x, self.y, self.z)
		# Convert heading from degrees to radians
		heading_radians = math.radians(self.heading)

		# Calculate x and y positions
		# In this coordinate system: x is based on sin, y is based on cos
		self.x += dt * self.xy_speed * math.sin(heading_radians)
		self.y += dt * self.xy_speed * math.cos(heading_radians)
		self.z += dt * self.z_speed

	def calc_next_pos_with_pos(self, target, dt):
		print("p", self.x, self.y, self.z)
		# Calculate the vector from current position to target
		dx = target[0] - self.x
		dy = target[1] - self.y
		dz = target[2] - self.z

		# Calculate the horizontal distance and total 3D distance
		horizontal_distance = math.sqrt(dx**2 + dy**2)

		# Calculate the maximum distance the object can move during dt
		xy_move_distance = dt * self.xy_speed
		z_move_distance = dt * self.z_speed


		if horizontal_distance <= xy_move_distance:
			# If the target is within reach, move directly to the target
			self.x = target[0]
			self.y = target[1]
		else:
			# Calculate horizontal heading using atan2
			heading_radians = math.atan2(dx, dy)  # Note: (x, y) order because 0° = North, increases clockwise

			# Calculate movement in x and y
			move_xy_distance = min(horizontal_distance, xy_move_distance)

			move_x = move_xy_distance * math.sin(heading_radians)
			move_y = move_xy_distance * math.cos(heading_radians)

			self.x += move_x
			self.y += move_y

		if dz <= z_move_distance:
			self.z = target[2]
		else:
			self.z += z_move_distance