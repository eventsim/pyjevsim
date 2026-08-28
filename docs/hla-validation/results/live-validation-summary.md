# Live RTI validation summary

These results cover application-visible functional behavior. Five separate
Pitch and Portico runs were recorded on 2026-08-19 during the v2.2.0
validation. After those changes were committed, each backend was run once
from a clean checkout of commit `ad9f54a6ee8b81694db2f42af2504b21e18779c4`;
both scenarios passed again. GORTI was qualified separately on 2026-08-28:
both scenarios were run in five sequential federation executions against one
`rtid` process, with the binary and Python bindings built from a clean archive
of GORTI commit
`475b23b7ea0e6714825c2d3cdbd5ec5c2f21bf6f`.

## Functional equivalence

The comparison requires exact equality of the sorted rows
`(tick, sense_id, x, y, z)` after coordinates are formatted with Python's
`%.10g` conversion. The committed CSV files name the identifier column
`object_name`; its values are the stable `sense_id` strings.

| Backend | Environment | Recorded runs | Result |
|---|---|---:|---|
| Pitch | pRTI Free 5.5.2; Temurin 11.0.31+11; JPype 1.7.1; CPython 3.11.15 | 5 | both 30-tick scenarios matched all 180 reference rows in every run |
| Portico | 2.1.4; `portico.connection=jvm`; Temurin 11.0.31+11; JPype 1.7.1; CPython 3.14.0 | 5 | both 30-tick scenarios matched all 180 reference rows in every run |
| GORTI (experimental pre-release) | commit `475b23b`; native Python SDK 0.9.0; grpcio 1.82.1; protobuf 7.35.1; CPython 3.11.15 | 5 sequential federation executions/scenario | both 30-tick scenarios matched all 180 reference rows in every execution |

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

For the GORTI qualification, `git archive HEAD` produced a clean source tree
with SHA-256
`e9ee4b5b86d3a6e6ba1f2e6890bd22f1e37732d30b91be1dea15e5d1a5af493f`.
The Python protocol bindings were regenerated from that tree and `rtid` was
built there. The resulting binary SHA-256 was
`afabcd83ce88d4955df24a6046a6a5e83d81f2724bbcbf612b9be9dc2d3c7bcc4`.
The pyjevsim GORTI connector exercised by this qualification was still a
pre-release, uncommitted artifact with SHA-256
`5640ccb14b0367e6b4d6ec1407102f32e9d98634874fea81b72ade806b9d79e5`;
the GORTI result must therefore be repeated from the eventual tagged
pyjevsim release before archive-ready evidence is declared.

## Toolchain files

- Pitch JAR SHA-256:
  `48c1545b89cc741610bef59abc0d7444439e35a693386365f0a509df56871978`
- Portico JAR SHA-256:
  `146dc0a7916b168396c6e595c42aaed0bdc69d64c5c54e728b7cb53fdd94ea84`
- Temurin `jvm.dll` SHA-256:
  `de36fc880fe3ec2bd027255b96d25060b1c426ba7cc38bd31e8551a9dfd50601`
- GORTI clean source archive SHA-256:
  `e9ee4b5b86d3a6e6ba1f2e6890bd22f1e37732d30b91be1dea15e5d1a5af493f`
- GORTI clean-tree `rtid` SHA-256:
  `afabcd83ce88d4955df24a6046a6a5e83d81f2724bbcbf612b9be9dc2d3c7bcc4`

## Test scope

The tests compare application-visible state on one physical host. They do not
test packet-level behavior, communication
performance, operation across physical hosts, interoperability with an
independently developed federate, or formal IEEE 1516 conformance.
