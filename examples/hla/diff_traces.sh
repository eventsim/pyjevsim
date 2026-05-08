#!/usr/bin/env bash
# Compare event-sequence traces from chat_pitch and chat_gorti runs.
#
# Run chat_pitch/run_demo.sh and chat_gorti/run_demo.sh first. Each
# script writes per-federate traces to /tmp/hla-traces/. This script
# diffs them and exits 0 on identical traces (gorti conformant with
# Pitch for the chat-federate scenario), non-zero otherwise.
#
# Usage:
#     ./examples/hla/diff_traces.sh
#     ./examples/hla/diff_traces.sh --color    # colorize via diff --color
#     ./examples/hla/diff_traces.sh --side     # side-by-side view
set -euo pipefail

DIR="${HLA_TRACE_DIR:-/tmp/hla-traces}"
DIFF_FLAGS=("-u")
case "${1:-}" in
    --color) DIFF_FLAGS=("-u" "--color=always") ;;
    --side)  DIFF_FLAGS=("-y" "--width=200") ;;
    "")      ;;
    *)       echo "unknown flag: $1"; exit 2 ;;
esac

missing=0
for f in alice.pitch.trace alice.gorti.trace bob.pitch.trace bob.gorti.trace; do
    if [[ ! -f "${DIR}/${f}" ]]; then
        echo "MISSING ${DIR}/${f}"
        missing=1
    fi
done
if [[ "${missing}" -ne 0 ]]; then
    echo
    echo "run both demos first:"
    echo "  ./examples/hla/chat_pitch/run_demo.sh"
    echo "  ./examples/hla/chat_gorti/run_demo.sh"
    exit 2
fi

rc=0
for who in alice bob; do
    echo "=== ${who}: pitch vs gorti ==="
    if diff "${DIFF_FLAGS[@]}" "${DIR}/${who}.pitch.trace" "${DIR}/${who}.gorti.trace"; then
        echo "  IDENTICAL — gorti matches Pitch for ${who}"
    else
        echo "  DIVERGENT — see diff above"
        rc=1
    fi
    echo
done

if [[ "${rc}" -eq 0 ]]; then
    echo "PASS: gorti traces match Pitch traces for both federates."
else
    echo "FAIL: gorti diverges from Pitch on at least one federate."
fi
exit "${rc}"
