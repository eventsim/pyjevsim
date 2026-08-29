"""Check trajectory artifacts and summary consistency without rerunning RTIs.

Live execution evidence is described separately; this script does not prove
that a recorded live campaign ran.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPOSITORY_ROOT = HERE.parents[2]
HEADER = ["tick", "object_name", "x", "y", "z"]
CURRENT_LIVE_MANIFEST = "live-acceptance-v2.2.0.json"


def _summary() -> list[dict[str, str]]:
    with (HERE / "equivalence-summary.csv").open(
        newline="", encoding="utf-8"
    ) as stream:
        return list(csv.DictReader(stream))


def main() -> None:
    summary = _summary()
    for scenario in ("self_propelled", "stationary"):
        path = HERE / f"expected_{scenario}.csv"
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        with path.open(newline="", encoding="utf-8") as stream:
            reader = csv.reader(stream)
            header = next(reader, None)
            if header != HEADER:
                raise SystemExit(f"unexpected header in {path}: {header!r}")
            rows = [
                (int(tick), object_name, x, y, z)
                for tick, object_name, x, y, z in reader
            ]

        records = [row for row in summary if row["scenario"] == scenario]
        if not records:
            raise SystemExit(f"missing equivalence summary for {scenario}")
        expected_count = int(records[0]["reference_rows"])
        if rows != sorted(rows):
            raise SystemExit(f"rows are not in numeric-tick tuple order: {path}")
        if len(set(rows)) != len(rows):
            raise SystemExit(f"duplicate canonical rows in {path}")
        if len(rows) != expected_count:
            raise SystemExit(
                f"row count mismatch for {scenario}: {len(rows)} != {expected_count}"
            )
        for record in records:
            reference_count = int(record["reference_rows"])
            federated_count = int(record["federated_rows"])
            expected_hash = record["canonical_reference_sha256"]
            if (
                reference_count != expected_count
                or federated_count != expected_count
                or record["first_divergence"] != "none"
            ):
                raise SystemExit(
                    f"inconsistent {record['backend']} summary for {scenario}"
                )
            if digest != expected_hash:
                raise SystemExit(
                    f"SHA-256 mismatch for {record['backend']}/{scenario}: "
                    f"{digest} != {expected_hash}"
                )
        backends = ",".join(record["backend"] for record in records)
        print(
            f"OK {scenario}: {len(rows)} rows, sha256={digest}, "
            f"records={backends}"
        )

    manifest_path = HERE / CURRENT_LIVE_MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    bindings = (
        manifest["validation_source_artifacts"]
        + manifest["reference_artifacts"]
    )
    for artifact in bindings:
        path = REPOSITORY_ROOT / artifact["path"]
        raw = path.read_bytes()
        if "sha256_lf" in artifact:
            checked = raw.replace(b"\r\n", b"\n")
            expected_size = artifact["size_lf"]
            expected_hash = artifact["sha256_lf"]
        else:
            checked = raw
            expected_size = artifact["size"]
            expected_hash = artifact["sha256"]
        actual_hash = hashlib.sha256(checked).hexdigest()
        if len(checked) != expected_size or actual_hash != expected_hash:
            raise SystemExit(f"live acceptance source binding mismatch: {path}")
    print(
        f"OK live acceptance manifest {CURRENT_LIVE_MANIFEST}: "
        f"{len(bindings)} source/reference bindings"
    )


if __name__ == "__main__":
    main()
