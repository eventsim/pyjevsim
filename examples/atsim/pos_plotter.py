import matplotlib
matplotlib.use('QtAgg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

class PositionPlotter:
    def __init__(self):
        """
        Initialize the 3D plot for the drone's trajectory.
        """
        self.x_positions = {}
        self.y_positions = {}
        self.z_positions = {}

        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(111, projection='3d')

        # Set up plot
        self.ax.set_xlabel('X (meters)')
        self.ax.set_ylabel('Y (meters)')
        self.ax.set_zlabel('Z (meters)')
        self.ax.set_title('Object Trajectory')

        # Set initial limits
        self.ax.set_xlim(-50, 50)
        self.ax.set_ylim(-50, 50)
        self.ax.set_zlim(0, 100)

        plt.ion()  # Turn on interactive mode
        plt.show()

    def update_position(self, obj_id, x, y, z, ocolor='red', tcolor='blue'):
        """
        Update the drone's position and redraw the trajectory.

        Parameters:
        x (float): New x-coordinate
        y (float): New y-coordinate
        z (float): New z-coordinate
        """
        if obj_id not in self.x_positions:
            self.x_positions[obj_id] = [x]
            self.y_positions[obj_id] = [y]
            self.z_positions[obj_id] = [z]
        else:
            self.x_positions[obj_id].append(x)
            self.y_positions[obj_id].append(y)
            self.z_positions[obj_id].append(z)

        #self.ax.clear()

        # Redraw the updated trajectory
        self.ax.plot(self.x_positions[obj_id], self.y_positions[obj_id], self.z_positions[obj_id], color=tcolor, label='Trajectory')
        self.ax.scatter(x, y, z, color=ocolor, s=50, label='Manuever Object')

        # Auto scale axis limits
        margin = 10
        self.ax.set_xlim(min((min(v) for k, v in self.x_positions.items()),key=lambda x: x) - margin, 
                         max((max(v) for k, v in self.x_positions.items()),key=lambda x: x) + margin)
        self.ax.set_ylim(min((min(v) for k, v in self.y_positions.items()),key=lambda x: x) - margin, 
                         max((max(v) for k, v in self.y_positions.items()),key=lambda x: x) + margin)
        self.ax.set_zlim(min((min(v) for k, v in self.z_positions.items()),key=lambda x: x) - margin, 
                         max((max(v) for k, v in self.z_positions.items()),key=lambda x: x) + margin)

        #self.ax.legend()
        plt.draw()
        plt.pause(0.01)  # Pause to update the plot