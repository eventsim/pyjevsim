# Publication review traceability

This publication-specific map records where Reviewer 1's requested items are
addressed and prevents the response letter from overstating what the repository
proves. It is kept separate from the capability-oriented HLA documentation and
does not replace the required point-by-point manuscript response.

## Major comments

| Comment | Repository response | Boundary/status |
|---|---|---|
| 1. Validation | [Validation model, setup, results, and provenance](README.md#2-validation-question-and-model); full FOM and two 180-row canonical traces; [compact live result and performance-characterization record](results/live-validation-summary.md) | Functional equivalence and same-host batch characterization only; no network or multi-host throughput/latency, raw-wire, or scalability result |
| 2. Behavioral equivalence | [Exact criterion and delivery-order scope](README.md#3-behavioral-equivalence-criterion); automated offline and live checkers; separate callback-order campaigns summarized in the live result record | Equivalence compares canonical application-state rows, not raw bytes, callback order, or wire traffic; callback results are a separate scoped observation |
| 3. RTI independence | Pitch pRTI Free 5.5.2 and open-source Portico 2.1.4 each completed five live AT/SIM invocations | Portico is an independent RTI implementation but its adapter subclasses Pitch; claim is limited to the connector/model-facing boundary, and the full local raw bundles are not yet in an immutable archive |
| 4. HLA time management | [Time mapping, grants, lookahead distinction, simultaneous events, backend behavior, and deadlock boundary](README.md#6-hla-time-management) | No NER, generic grant timeout, deadlock recovery, or TSO claim for Portico |
| 5. Figures | [Architecture and sequence diagrams](README.md#1-architecture) | Mermaid sources are stored with the implementation documentation |
| 6. Related work | [Comparison and references](related-work.md) | The two-page manuscript still needs a compact positioning sentence and selected citations |
| 7. Reproducibility | Direct validation dependencies, FOM/scenarios, exact commands, full expected traces, tests, Java-free CI gate, bundled same-JVM Portico RID, and compact live environment/result record | **Pending:** archive or rerun the full raw live bundles against the final clean revision, then create consistent version metadata and a new immutable archive/DOI; the v2.1.2 DOI predates AT/SIM and Portico |
| 8. Compliance claims | [IEEE 1516 service coverage](ieee1516-support.md) uses “IEEE 1516-2010-based” and enumerates implemented/omitted services | No formal conformance testing is claimed |

## Minor comments

| Requested item | Repository action or disposition |
|---|---|
| Change the article title | Manuscript-only decision. The journal's software-update form fixes the title, so no repository title is changed. Explain this constraint in the response letter. |
| Use one software version | Existing v2.1.2 tag/DOI remains immutable. The validation revision must receive its own final commit/archive rather than moving the tag. |
| Explain the two backend hooks | Signatures and responsibilities are in [Reuse and extension](README.md#7-reuse-and-extension) and [`rti_interface.md`](../hla/rti_interface.md). |
| Define abbreviations | DEVS, HLA, RTI, FOM, TSO, RO, and JPype are defined in the [terms list](README.md#terms). |
| Compare previous/current releases | The [release comparison](README.md#release-comparison) separates the published baseline, v2.1.2, and the current validation revision. |
| Validate interactions and attributes | The [evidence-path table](README.md#2-validation-question-and-model) states which example exercises each path. |
| Explain `inout` and invalid directions | Runtime construction and publish/subscribe guards are tested in [`test_m0_foundation.py`](../../tests/hla/test_m0_foundation.py) and [`test_rti_interface.py`](../../tests/hla/test_rti_interface.py). |
| Explain lifecycle errors | The [error policy](ieee1516-support.md#error-propagation-policy) distinguishes propagated setup/runtime errors from best-effort cleanup. |
| Add limitations/future work | [Limitations and future work](README.md#8-limitations-and-future-work). |
| Add immutable code identifier | Core v2.1.2 identifiers are recorded, but a new archive for the validation revision is still required. |
| Add outputs to abstract/conclusion and edit PDF | Manuscript-only work; not represented as completed by repository changes. |
