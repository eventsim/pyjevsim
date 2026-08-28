Anti-Torpedo Simulation Example
===============================

This synthetic example models a surface ship, a torpedo, detection and control
components, and two decoy types. It demonstrates coupled DEVS models,
scenario-driven configuration, plotting, and snapshot/restore in pyjevsim.

Scenario behavior
-----------------

- The surface ship and torpedo move from positions and headings defined by a
  YAML scenario.
- Detector models report nearby objects to their command-and-control models.
- The ship deploys decoys and changes heading when the torpedo reaches the
  configured engagement range.
- The torpedo selects the closest detected ship or decoy as its target.
- Decoy launch parameters and lifetime are read from the scenario.

Run
---

From the repository root:

.. code-block:: console

   $ python -m pip install -e . -r examples/atsim/requirements.txt
   $ python examples/atsim/simulator.py

An optional numeric argument sets the pause between plotted frames. The
``simulator_snapshot.py`` and ``simulator_restore.py`` scripts demonstrate
snapshot creation and restore.

Scope
-----

The example uses simplified equations, algorithms, and synthetic parameters to
show pyjevsim features. It is not intended for operational analysis.

References
----------

- K.-M. Seo et al., “Measurement of effectiveness for an anti-torpedo combat
  system using a discrete event systems specification-based underwater
  warfare simulator,” *The Journal of Defense Modeling and Simulation*, 8(3),
  157–171, 2011.
- T. G. Kim et al., “DEVSim++ toolset for defense modeling and simulation and
  interoperation,” *The Journal of Defense Modeling and Simulation*, 8(3),
  129–142, 2011.
