#!/usr/bin/env bash
# Trace-oracle gate; .github/workflows/oracle.yml runs it, and it runs the
# same way locally from any directory of a clone:
#
#   tools/oracle/ci_gate.sh [BASE_REF]          (default BASE_REF: origin/main)
#
# 1. Exports the merge base of HEAD and BASE_REF with `git archive`, runs the
#    oracle in hash mode on the export and on the working tree, and fails if
#    a verdict scenario differs, unless both the ledger and the golden (a
#    golden file, or GOLDEN in trace_oracle.py) changed since the merge
#    base; then the difference is a warning. Informational differences are
#    warnings.
# 2. Compares the working tree with the golden and fails on any verdict
#    difference. A changed golden without a ledger change fails too.
#
# Environment:
#   ORACLE_BASE    commit to use instead of the merge base (a trial run can
#                  use HEAD~1; the workflow passes the pushed-over commit)
#   ORACLE_ARGS    extra oracle arguments for both runs, e.g. --no-slow
#   ORACLE_GOLDEN  golden file (default: GOLDEN in trace_oracle.py)
#   PYTHON         interpreter (default python)
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
py=${PYTHON:-python}
oracle=tools/oracle/trace_oracle.py
golden=${ORACLE_GOLDEN:-$(cd tools/oracle && "$py" -c 'import trace_oracle; print(trace_oracle.GOLDEN)')}
ledger=tools/oracle/LEDGER.md
base=${ORACLE_BASE:-}
if [ -z "$base" ] || [ -z "${base//0/}" ]; then
    base=$(git merge-base HEAD "${1:-origin/main}")
fi
base=$(git rev-parse --verify "$base^{commit}")

work=$(mktemp -d)
# Git for Windows: hand Python a native path.
if command -v cygpath >/dev/null 2>&1; then work=$(cygpath -m "$work"); fi
trap 'rm -rf "$work"' EXIT

note() {  # level message
    if [ "${GITHUB_ACTIONS:-}" = true ]; then
        echo "::$1 title=trace oracle::$2"
    else
        echo "$1: $2"
    fi
}

annotate() {  # level file pattern
    grep -E "$3" "$2" | while IFS= read -r line; do note "$1" "$line"; done || true
}

echo "merge base: $base"
echo "HEAD:       $(git rev-parse HEAD)"
mkdir "$work/base"
git archive "$base" | (cd "$work/base" && tar -x)

# A scenario error is part of the digest; the comparisons below decide.
# shellcheck disable=SC2086
"$py" "$oracle" --repo "$work/base" --label "merge base $base" --out "$work/base.json" \
    --hash-only ${ORACLE_ARGS:-} || true
# shellcheck disable=SC2086
"$py" "$oracle" --label HEAD --out "$work/head.json" \
    --hash-only ${ORACLE_ARGS:-} || true

status=0

changed=$(git diff --name-only "$base...HEAD")
ledger_changed=no
if printf '%s\n' "$changed" | grep -qxF "$ledger"; then ledger_changed=yes; fi
golden_pointer() {  # commit
    git show "$1:$oracle" 2>/dev/null | grep -E '^GOLDEN[[:space:]]*=' || true
}
golden_changed=no
if [ -n "$(git diff --name-only --diff-filter=AM "$base...HEAD" -- tools/oracle/golden/)" ] \
        || [ "$(golden_pointer "$base")" != "$(golden_pointer HEAD)" ]; then
    golden_changed=yes
fi

echo
echo "== merge base vs HEAD"
if "$py" "$oracle" --compare "$work/base.json" "$work/head.json" > "$work/merge_base.txt"; then
    cat "$work/merge_base.txt"
else
    cat "$work/merge_base.txt"
    if [ "$ledger_changed" = yes ] && [ "$golden_changed" = yes ]; then
        annotate warning "$work/merge_base.txt" '^(DIFF|ERROR|MISSING) '
        echo "HEAD differs from the merge base; $ledger and the golden changed in this change set, so the difference is recorded. The golden comparison below must match."
    else
        annotate error "$work/merge_base.txt" '^(DIFF|ERROR|MISSING) '
        note error "A verdict scenario differs from the merge base. A performance-only change must leave every verdict hash unchanged; an intended semantic change must add a $ledger entry and a new golden, and point GOLDEN in $oracle at it, in the same pull request. See tools/oracle/README.md and CONTRIBUTING.md."
        status=1
    fi
fi
annotate warning "$work/merge_base.txt" '^(INFO-DIFF|INFO-ERROR|WARN) '

echo
echo "== golden vs HEAD ($golden)"
if "$py" "$oracle" --compare "$golden" "$work/head.json" > "$work/golden.txt"; then
    cat "$work/golden.txt"
else
    cat "$work/golden.txt"
    annotate error "$work/golden.txt" '^(DIFF|ERROR|MISSING) '
    note error "HEAD differs from $golden. Either the change alters behaviour it should not, or the golden was not regenerated from this tree (or GOLDEN not pointed at the new one); see tools/oracle/README.md."
    status=1
fi
if [ "$golden_changed" = yes ] && [ "$ledger_changed" = no ]; then
    note error "The golden changed (a file under tools/oracle/golden/ or GOLDEN in $oracle) without an entry in $ledger."
    status=1
fi

exit "$status"
