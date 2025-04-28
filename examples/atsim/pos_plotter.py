import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

class PositionPlotter:
    def __init__(self):
        """
        Initialize the 3D plot for the drone's trajectory.
        """
        self.x_positions = []
        self.y_positions = []
        self.z_positions = []

        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(111, projection='3d')

        # Set up plot
        self.ax.set_xlabel('X (meters)')
        self.ax.set_ylabel('Y (meters)')
        self.ax.set_zlabel('Z (meters)')
        self.ax.set_title('Drone Trajectory')

        # Set initial limits
        self.ax.set_xlim(-50, 50)
        self.ax.set_ylim(-50, 50)
        self.ax.set_zlim(0, 100)

        plt.ion()  # Turn on interactive mode
        plt.show()

    def update_position(self, x, y, z):
        """
        Update the drone's position and redraw the trajectory.

        Parameters:
        x (float): New x-coordinate
        y (float): New y-coordinate
        z (float): New z-coordinate
        """
        self.x_positions.append(x)
        self.y_positions.append(y)
        self.z_positions.append(z)

        self.ax.clear()

        # Redraw the updated trajectory
        self.ax.plot(self.x_positions, self.y_positions, self.z_positions, color='blue', label='Trajectory')
        self.ax.scatter(x, y, z, color='red', s=50, label='Drone')

        # Reapply labels and title
        self.ax.set_xlabel('X (meters)')
        self.ax.set_ylabel('Y (meters)')
        self.ax.set_zlabel('Z (meters)')
        self.ax.set_title('Drone Trajectory')

        # Auto scale axis limits
        margin = 10
        self.ax.set_xlim(min(self.x_positions) - margin, max(self.x_positions) + margin)
        self.ax.set_ylim(min(self.y_positions) - margin, max(self.y_positions) + margin)
        self.ax.set_zlim(0, max(self.z_positions) + margin)

        self.ax.legend()
        plt.draw()
        plt.pause(0.01)  # Pause to update the plot