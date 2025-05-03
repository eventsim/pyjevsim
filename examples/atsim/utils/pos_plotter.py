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
        self.ax.set_xlim(-150, 150)
        self.ax.set_ylim(-150, 150)
        self.ax.set_zlim(-50, 100)

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

        self.ax.clear()

        # Set up plot
        self.ax.set_xlabel('X (meters)')
        self.ax.set_ylabel('Y (meters)')
        self.ax.set_zlabel('Z (meters)')
        self.ax.set_title('Object Trajectory')

        # Redraw the updated trajectory
        for oid in self.x_positions:
            self.ax.plot(
            self.x_positions[oid],
            self.y_positions[oid],
            self.z_positions[oid],
            label=f'Trajectory {oid}'
            )

            self.ax.scatter(
            self.x_positions[oid][-1],
            self.y_positions[oid][-1],
            self.z_positions[oid][-1],
            s=50,
            label=f'Object {oid}'
            )

        # Auto scale axis limits
        margin = 10
        all_x = sum(self.x_positions.values(), [])
        all_y = sum(self.y_positions.values(), [])
        all_z = sum(self.z_positions.values(), [])
        self.ax.set_xlim(min(all_x) - margin, max(all_x) + margin)
        self.ax.set_ylim(min(all_y) - margin, max(all_y) + margin)
        self.ax.set_zlim(min(all_z) - margin, max(all_z) + margin)

        #self.ax.legend()
        plt.draw()
        plt.pause(0.01)  # Pause to update the plot

    def terminate_plot(self):
        plt.close()