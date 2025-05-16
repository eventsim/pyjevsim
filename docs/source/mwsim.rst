
Municipal Waste Management Simulator
====================================

Introduction
------------

The **Municipal Waste Management Simulator** is an agent-based simulation designed for evaluating urban waste management policies. It predicts waste generation based on resident types and their distribution, reflecting distinct lifestyle patterns across various residential groups. Additionally, it simulates resident satisfaction levels depending on waste collection frequency and methods.

The simulator models diverse resident behaviors and residential types, enabling the generation of waste disposal patterns specific to single or multi-person households and residential area characteristics. It also includes models for trash bins and waste collection vehicles, facilitating simulation of various waste collection strategies, especially focused on urban residential areas over long-term scenarios. Thus, the model addresses changes in population dynamics and adjusts waste collection policies accordingly.

Scenario Explanation
--------------------

- **Resident Daily Pattern:** Residents leave their homes in the morning and return in the evening.
- **Waste Disposal:** Residents dispose of waste when leaving their homes.
- **Resident Satisfaction:** Dissatisfaction increases when residents find local waste bins already full.
- **Waste Collection Vehicles:** Waste is collected according to government-defined collection policies.
- **Collection Method:** Vehicles collect all waste from bins within residential areas if capacity allows.
- **Capacity Constraints:** If a collection vehicle lacks sufficient capacity, it collects only as much waste as possible before returning to base.

Save and Restore Functionality
------------------------------

- The simulator utilizes pyjevsim to save simulation states at specific points, enabling detailed analysis of waste disposal patterns and resident dissatisfaction based on changes in population demographics and distributions.
- Users can restore saved states, adjust resident type and distribution, and analyze the outcomes of modified scenarios.

Important Notes
---------------

Sensitive information has been deliberately excluded to focus solely on fundamental capabilities.

References
----------

- Lyoo, Chang-Hyun, et al. "Modeling and simulation of a municipal solid waste management system based on discrete event system specification." *Proceedings of the 11th Annual Symposium on Simulation for Architecture and Urban Design*, 2020.
