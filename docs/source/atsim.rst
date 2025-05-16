
Anti-Torpedo Simulator
======================

Introduction
------------

The **Anti-Torpedo Simulator** is designed to enhance surface ship survivability against torpedo threats. It allows testing of tactical decoy strategies and supports evaluation and acquisition of advanced decoy systems.

For instance, users can compare survivability outcomes by integrating new self-propelled decoy systems against traditional stationary decoy systems, using existing ship and torpedo simulation models.

Scenario Explanation
--------------------

- **Surface Ship Movement:** Moves according to scenario-defined heading parameters.
- **Detection Model:** Executes detection algorithms based on positional data of surrounding objects and transmits detection results to the ship's Command and Control (C2) system.
- **Command and Control System:** Calculates distances to detected torpedoes, deploys decoys upon reaching torpedo engagement range, and initiates evasive maneuvers using predefined evasion headings.
- **Decoy Deployment:** Launch parameters (elevation, azimuth, launch speed) are scenario-defined.
- **Decoy Lifecycle:** Continuously updates positional data throughout its predefined lifespan.
- **Torpedo Movement:** Navigates according to the scenario heading; its detection model transmits target locations to the torpedo's C2 system.
- **Torpedo Targeting:** The torpedo’s C2 system directs the torpedo toward the closest detected target (ship or decoy).

Save and Restore Functionality
------------------------------

The simulator includes a save-and-restore feature enabling repeated experimentation from specific decoy deployment points. This allows comparison and analysis of multiple decoy systems under consistent simulation conditions.

Important Notes
---------------

The simulation model contains simplified versions of equations of motion, detection algorithms, and Command and Control functionalities. Sensitive information has been deliberately excluded to focus solely on fundamental capabilities.

References
----------

- Seo, Kyung-Min, et al. "Measurement of effectiveness for an anti-torpedo combat system using a discrete event systems specification-based underwater warfare simulator." *The Journal of Defense Modeling and Simulation*, vol. 8, no. 3, 2011, pp. 157–171.
- Kim, Tag Gon, et al. "DEVSim++ toolset for defense modeling and simulation and interoperation." *The Journal of Defense Modeling and Simulation*, vol. 8, no. 3, 2011, pp. 129–142.
