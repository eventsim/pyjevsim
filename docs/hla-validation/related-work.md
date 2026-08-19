# Related work and contribution boundary

pyjevsim builds on established work in DEVS execution, distributed DEVS, and
DEVS/HLA integration. The project contribution documented here is deliberately
narrow: an existing Python DEVS model keeps its ordinary port API while
declarative bindings and a small `RTIConnector` boundary select among multiple
RTIs at runtime; the same core tick is used in standalone and HLA-driven modes.

## Positioning

| System/approach | Primary emphasis | Relationship to pyjevsim HLA |
|---|---|---|
| PythonPDEVS | Classic/Parallel DEVS with parallel and distributed simulation in Python | A Python-native distributed DEVS engine. pyjevsim instead adds an IEEE 1516 RTI boundary to its existing model/executor API. |
| xDEVS | A common DEVS API across Java, C++, and Python, with sequential, parallel, and distributed architectures | Broader cross-language DEVS interoperability. pyjevsim's narrower contribution is runtime-pluggable HLA transports plus model-port bindings. |
| DEVS/HLA and G-DEVS/HLA work | Mapping DEVS-family models and time semantics onto HLA federations | Establishes the conceptual basis for combining DEVS and HLA. pyjevsim contributes a compact Python implementation, codec/transport separation, and preserved application model code. |
| DEVSim++ ME / KHLA Adaptor | C++ DEVS model engineering, verification/validation tools, and an HLA adaptor | A mature toolchain-oriented integration. pyjevsim targets a smaller, Python-facing extension surface and ships offline plus two live backend paths. |
| HLA Development Kit | RTI-independent Java APIs and annotations for common HLA federate services | A prior general-purpose RTI abstraction. pyjevsim does not claim first RTI independence; its narrower scope is a Python DEVS port-binding/executor integration. |
| pyjevsim 2025 | Python DEVS execution with model/simulation journaling | The HLA extension retains that API and adds federated execution; it does not replace or re-evaluate the original journaling contribution. |

The table is a scope comparison, not a feature-completeness ranking.  In
particular, pyjevsim does not claim to replace distributed-DEVS algorithms,
model-engineering environments, or complete HLA federation-development tools.
It also does not claim to be the first distributed DEVS engine, DEVS/HLA
bridge, or RTI abstraction. The scoped contribution is the combination of
external per-port descriptors, an executor layer that keeps RTI calls out of
ordinary `BehaviorModel` implementations, and a runtime-selectable
connector/capability/codec boundary in Python.

## References

1. J. Lee, G. Ham, S. Jang, S. Kang, and C. Choi, “pyjevsim:
   Streamlining simulation workflows using journaling in Python-based discrete
   event simulation environments,” *SoftwareX* 31 (2025), 102291.
   <https://doi.org/10.1016/j.softx.2025.102291>
2. Y. Van Tendeloo and H. Vangheluwe, “PythonPDEVS: a distributed parallel
   DEVS simulator,” SpringSim/TMS-DEVS (2015), pp. 91-98.
   <https://dblp.org/rec/conf/springsim/TendelooV15>
3. J. L. Risco-Martín, S. Mittal, K. Henares, R. Cárdenas, and P. Arroba,
   “xDEVS: A toolkit for interoperable modeling and simulation of formal
   discrete event systems,” *Software: Practice and Experience* 53(3)
   (2023), 748-789. <https://doi.org/10.1002/spe.3168>
4. B. P. Zeigler and J. S. Lee, “Theory of Quantized Systems: Formal Basis
   for DEVS/HLA Distributed Simulation Environment,” *Proceedings of SPIE*
   3369 (1998), 49-58. <https://doi.org/10.1117/12.319354>
5. G. Zacharewicz, C. Frydman, and N. Giambiasi, “G-DEVS/HLA Environment for
   Distributed Simulations of Workflows,” *SIMULATION* 84(5) (2008), 197-213.
   <https://doi.org/10.1177/0037549708092833>
6. T. G. Kim and C. Choi, “DEVSim++ ME: HLA-Compliant DEVS
   Modeling/Simulation Environment With DEVSim++,” in *Model Engineering for
   Simulation* (2019), pp. 355-392.
   <https://doi.org/10.1016/B978-0-12-813543-3.00017-2>
7. A. Falcone, A. Garro, A. Anagnostou, N. R. Chaudhry, A. Salah, and
   S. J. E. Taylor, “Experiences in simplifying distributed simulation: the
   HLA Development Kit framework,” *Journal of Simulation* 11(3) (2017),
   208-227. <https://doi.org/10.1057/s41273-016-0039-4>
