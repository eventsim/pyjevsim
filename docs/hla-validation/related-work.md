# Related projects

pyjevsim builds on established work in DEVS execution, distributed DEVS, and
DEVS/HLA integration. Its HLA layer connects named `BehaviorModel` ports to a
selected RTI through external bindings and FOM configuration. RTI calls stay
outside the model class, and standalone and HLA-driven execution share the same
simulation tick.

## Comparison

| System/approach | Primary emphasis | Relationship to pyjevsim HLA |
|---|---|---|
| PythonPDEVS | Classic/Parallel DEVS with parallel and distributed simulation in Python | Distributed scheduling is native to its Python kernel; pyjevsim instead connects its existing executor to an IEEE 1516 RTI. |
| xDEVS | A common DEVS API across Java, C++, and Python, with sequential, parallel, and distributed architectures | Its scope is a multi-language DEVS API and execution family; pyjevsim uses external port bindings and selectable HLA connectors. |
| DEVS/HLA and G-DEVS/HLA work | Mapping DEVS-family models and time semantics onto HLA federations | The conceptual mapping predates this project; pyjevsim supplies a concrete Python binding, codec, and connector layer. |
| DEVSim++ ME / KHLA Adaptor | C++ DEVS model engineering, verification/validation tools, and an HLA adaptor | A C++ model-engineering stack with an HLA adaptor, in contrast to pyjevsim's Python model API. |
| HLA Development Kit | RTI-independent Java APIs and annotations for common HLA federate services | Java annotation and service abstractions; pyjevsim selects connectors in executor configuration and binds named model ports. |
| pyjevsim 2025 | Python DEVS execution with model/simulation journaling | Baseline model API retained by the HLA extension; the original journaling contribution is not re-evaluated here. |

pyjevsim focuses on connecting existing `BehaviorModel` ports to selectable
HLA backends. It is not a replacement for a distributed-DEVS scheduler, a
model-engineering environment, or a complete federation-development toolkit.

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
