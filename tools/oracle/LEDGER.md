# Golden-change ledger

Every change to a trace-oracle golden, and every merged pull request that
makes a verdict scenario differ from the committed golden, gets an entry
here, newest first, in the same pull request. The CI job fails a golden
mismatch, or a changed golden file, unless this file changed too.

An entry records:

- **Date** of the merge (YYYY-MM-DD).
- **PR**: the pull request number, and the commit that was measured.
- **Scenarios changed**: each verdict scenario whose hash moved, with the
  old and new sha256 prefixes (informational scenarios only if a golden
  regeneration touched them).
- **Why**: the observable behaviour that changed and the reason it is
  intended. Name the CHANGELOG entry. A performance-only pull request
  should never need an entry; if it does, split it (see CONTRIBUTING.md).
- **Approved by**: the maintainer who accepted the change (the person who
  applied the `semantic-change` label).

Regenerate a golden with
`python tools/oracle/trace_oracle.py --repo <export> --golden <file> --write-golden`
and say in the entry which checkout, Python version and platform produced it.

---

## 2026-10-23 — freeze the v2.2.0 golden

- **PR**: the pull request that adds `tools/oracle/` (branch
  `infra/trace-oracle`).
- **Scenarios changed**: none; first golden. `golden/v2.2.0.json` holds
  all 18 scenarios (15 verdict, 3 informational), produced with
  `--write-golden` from `git archive 9a2b0d2` (the last main before #41:
  v2.2.0 plus the documentation PR #40) on CPython 3.14.0, Windows 11
  x86-64.
- **Why**: fixes the observable behaviour of v2.2.0 as the reference for
  the 2.3.0 performance release. Main at `f7145e6` (after #41, #42, #43
  and #44) reproduces every scenario hash, including the three
  informational ones at the pinned salt; so does the same tree under
  CPython 3.13.13. The digest taken at `b447f6f`, against which #41, #42
  and #44 were checked, matches as well.
- **Approved by**: pending maintainer review (Changbeom Choi).
