# Live RTI validation summary

These results cover application-visible functional behavior. Five separate
runs per backend were recorded on 2026-08-19 during the v2.2.0 validation.
After those changes were committed, each backend was run once
from a clean checkout of commit `ad9f54a6ee8b81694db2f42af2504b21e18779c4`;
both scenarios passed again.

## Functional equivalence

The comparison requires exact equality of the sorted rows
`(tick, sense_id, x, y, z)` after coordinates are formatted with Python's
`%.10g` conversion. The committed CSV files name the identifier column
`object_name`; its values are the stable `sense_id` strings.

| Backend | Environment | Recorded runs | Result |
|---|---|---:|---|
| Pitch | pRTI Free 5.5.2; Temurin 11.0.31+11; JPype 1.7.1; CPython 3.11.15 | 5 | both 30-tick scenarios matched all 180 reference rows in every run |
| Portico | 2.1.4; `portico.connection=jvm`; Temurin 11.0.31+11; JPype 1.7.1; CPython 3.14.0 | 5 | both 30-tick scenarios matched all 180 reference rows in every run |

The reference SHA-256 values are
`0a63baaf7095c646d88a082197bf3a0cb65fe5a278781c37b00f35fe45a0a205`
for `self_propelled` and
`2357658121aa36ad4c7f17431b2e1084d577fcd0e45abe1d2d184d4f1764549c`
for `stationary`. Each hash covers the UTF-8 CSV header and numerically sorted
rows with LF line endings.

The later clean-checkout run also checked the bundled Portico same-JVM
configuration and the missing-peer failure path. Its
[machine-readable manifest](live-acceptance-manifest.json) records source,
configuration, toolchain, return codes, and output hashes. It was generated
before the v2.2.0 tag and records `archive_ready: false`.

## Toolchain files

- Pitch JAR SHA-256:
  `48c1545b89cc741610bef59abc0d7444439e35a693386365f0a509df56871978`
- Portico JAR SHA-256:
  `146dc0a7916b168396c6e595c42aaed0bdc69d64c5c54e728b7cb53fdd94ea84`
- Temurin `jvm.dll` SHA-256:
  `de36fc880fe3ec2bd027255b96d25060b1c426ba7cc38bd31e8551a9dfd50601`

## Test scope

The tests compare application-visible state on one physical host. They do not
test packet-level behavior, communication
performance, operation across physical hosts, interoperability with an
independently developed federate, or formal IEEE 1516 conformance.
