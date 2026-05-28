import signal

import matplotlib
matplotlib.use('QtAgg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

class PositionPlotter:
    """Live 3D trajectory plot.

    Real-time pacing is done here on the GUI thread via ``plt.pause`` —
    *not* by running the simulator in ``R_TIME`` mode. ``R_TIME`` sleeps
    on the main thread, which is also the thread Qt pumps its event loop
    on, so the window goes "Not Responding" for the whole sleep and only
    repaints in the brief gap between steps. Driving the simulator in
    ``V_TIME`` and letting ``render(pause=...)`` provide the delay keeps
    the window interactive the entire time.

    Usage per frame::

        for obj in objects:
            plotter.update_position(name, x, y, z)   # buffer only
        plotter.render(pause=0.3)                     # one repaint + wait
    """

    def __init__(self):
        """Initialize the 3D plot for the object trajectories."""
        self.x_positions = {}
        self.y_positions = {}
        self.z_positions = {}
        self.colors = {}  # obj_id -> (point_color, line_color)

        # Make Ctrl+C terminate the process. plt.pause / plt.show run
        # Qt's C-level event loop, which never hands control back to the
        # Python interpreter, so a SIGINT can't raise KeyboardInterrupt
        # and the program appears unkillable. Restoring the OS default
        # SIGINT handler lets Ctrl+C kill it immediately. Must run on the
        # main thread (the simulators create the plotter there).
        try:
            signal.signal(signal.SIGINT, signal.SIG_DFL)
        except (ValueError, OSError):
            # Not on the main thread — leave the default handler in place.
            pass

        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(111, projection='3d')

        self._setup_axes()

        # Initial limits (overwritten by autoscale once data arrives)
        self.ax.set_xlim(-150, 150)
        self.ax.set_ylim(-150, 150)
        self.ax.set_zlim(-50, 100)

        plt.ion()  # Interactive mode so the window paints without blocking
        plt.show()

    def _setup_axes(self):
        self.ax.set_xlabel('X (meters)')
        self.ax.set_ylabel('Y (meters)')
        self.ax.set_zlabel('Z (meters)')
        self.ax.set_title('Object Trajectory')

    def update_position(self, obj_id, x, y, z, ocolor='red', tcolor='blue'):
        """Buffer a new position for ``obj_id``.

        This only appends to the trajectory history; it does **not**
        repaint. Call :meth:`render` once per frame after updating every
        object so the scene is drawn a single time and the GUI event loop
        is serviced.

        Parameters:
            obj_id (str): trajectory identifier
            x, y, z (float): new coordinates
            ocolor (str): marker colour for the current position
            tcolor (str): line colour for the trajectory
        """
        if obj_id not in self.x_positions:
            self.x_positions[obj_id] = [x]
            self.y_positions[obj_id] = [y]
            self.z_positions[obj_id] = [z]
        else:
            self.x_positions[obj_id].append(x)
            self.y_positions[obj_id].append(y)
            self.z_positions[obj_id].append(z)

        self.colors[obj_id] = (ocolor, tcolor)

    def render(self, pause=0.0):
        """Repaint every buffered trajectory once and service the GUI.

        Args:
            pause (float): seconds to keep the GUI event loop running
                before returning. A positive value both paces the
                animation and keeps the window responsive (``plt.pause``
                pumps the backend event loop for the whole duration). A
                zero/omitted value just flushes pending events.
        """
        if not self.x_positions:
            return

        self.ax.clear()
        self._setup_axes()

        for oid in self.x_positions:
            ocolor, tcolor = self.colors.get(oid, ('red', 'blue'))
            self.ax.plot(
                self.x_positions[oid],
                self.y_positions[oid],
                self.z_positions[oid],
                color=tcolor,
                label=f'Trajectory {oid}',
            )
            self.ax.scatter(
                self.x_positions[oid][-1],
                self.y_positions[oid][-1],
                self.z_positions[oid][-1],
                s=50,
                color=ocolor,
                label=f'Object {oid}',
            )

        # Auto scale axis limits
        margin = 10
        all_x = sum(self.x_positions.values(), [])
        all_y = sum(self.y_positions.values(), [])
        all_z = sum(self.z_positions.values(), [])
        self.ax.set_xlim(min(all_x) - margin, max(all_x) + margin)
        self.ax.set_ylim(min(all_y) - margin, max(all_y) + margin)
        self.ax.set_zlim(min(all_z) - margin, max(all_z) + margin)

        if pause > 0:
            # plt.pause draws the canvas AND runs the GUI event loop for
            # `pause` seconds, so the window stays responsive.
            plt.pause(pause)
        else:
            self.fig.canvas.draw_idle()
            self.fig.canvas.flush_events()

    def keep_open(self):
        """Block on the window after the run so it stays interactive.

        Without this the script exits as soon as the simulation loop
        ends and the (interactive-mode) window vanishes — leaving the
        impression that it "froze" and disappeared.
        """
        plt.ioff()
        plt.show()

    def terminate_plot(self):
        plt.close()
