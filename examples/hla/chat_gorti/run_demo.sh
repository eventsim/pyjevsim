#!/usr/bin/env bash
# Orchestrate the gorti two-federate chat demo.
#
# Spawns one rtid (gorti server) and two pyjevsim federates (alice, bob)
# pointed at it via gRPC. Waits for the federates to finish, prints
# their captured chat output, then tears down rtid.
#
# Usage:
#     ./run_demo.sh                         # default: 5 messages each, 10s sim
#     COUNT=3 PERIOD=0.5 END=8 ./run_demo.sh
#     RTID=/path/to/rtid PORT=7000 ./run_demo.sh
#
# Requirements:
#   - gorti rtid binary (built from the gorti repo: `go build -o rtid ./cmd/rtid`)
#   - pyjevsim + rti1516e (gorti pysdk) pip-installed in the active Python env
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
GORTI_DIR="${GORTI_DIR:-${REPO_ROOT}/../gorti}"
RTID="${RTID:-${GORTI_DIR}/rtid}"
PORT="${PORT:-7100}"
COUNT="${COUNT:-5}"
PERIOD="${PERIOD:-1.0}"
END="${END:-10.0}"

if [[ ! -x "${RTID}" ]]; then
    echo "FATAL: rtid binary not found at ${RTID}"
    echo "  build it from the gorti repo: (cd ${GORTI_DIR} && go build -o rtid ./cmd/rtid)"
    exit 2
fi
if ! python3 -c "import rti1516e" 2>/dev/null; then
    echo "FATAL: 'rti1516e' python package is not installed in this venv"
    echo "  pip install -e ${GORTI_DIR}/pysdk"
    exit 2
fi

LOG_DIR="$(mktemp -d -t hla-chat-gorti.XXXXXX)"
echo "log dir: ${LOG_DIR}"

PIDS=()
cleanup() {
    set +e
    echo
    echo "-- shutting down (PIDS=${PIDS[*]}) --"
    for pid in "${PIDS[@]}"; do
        if kill -0 "${pid}" 2>/dev/null; then
            kill -TERM "${pid}" 2>/dev/null || true
        fi
    done
    sleep 0.5
    for pid in "${PIDS[@]}"; do
        if kill -0 "${pid}" 2>/dev/null; then
            kill -KILL "${pid}" 2>/dev/null || true
        fi
    done
}
trap cleanup EXIT INT TERM

echo "starting rtid on :${PORT}  (log: ${LOG_DIR}/rtid.log)"
"${RTID}" --listen ":${PORT}" >"${LOG_DIR}/rtid.log" 2>&1 &
PIDS+=("$!")
RTID_PID="${PIDS[0]}"

# Wait for rtid to be listening — try a quick TCP probe with /dev/tcp.
for _ in $(seq 1 20); do
    if (echo > "/dev/tcp/127.0.0.1/${PORT}") 2>/dev/null; then
        break
    fi
    sleep 0.2
done
if ! (echo > "/dev/tcp/127.0.0.1/${PORT}") 2>/dev/null; then
    echo "FATAL: rtid did not start listening on :${PORT} within 4s"
    echo "  see ${LOG_DIR}/rtid.log"
    exit 3
fi

start_federate() {
    local name="$1"; shift
    local logfile="${LOG_DIR}/${name}.log"
    local tracefile="${LOG_DIR}/${name}.trace"
    echo "starting federate ${name}  (log: ${logfile}, trace: ${tracefile})"
    ( cd "${REPO_ROOT}" && python3 -m examples.hla.chat_gorti.run "${name}" \
        --url "grpc://localhost:${PORT}" --count "${COUNT}" \
        --period "${PERIOD}" --end "${END}" --log INFO \
        --trace-file "${tracefile}" >"${logfile}" 2>&1 ) &
    PIDS+=("$!")
}

start_federate alice
start_federate bob

# Wait for both federates to finish; ignore exit codes so cleanup runs.
wait "${PIDS[1]}" "${PIDS[2]}" || true

echo
echo "-- federate output ----------------------------------------------"
for name in alice bob; do
    echo "## ${name}.log"
    grep -E '\[(alice|bob)\] heard' "${LOG_DIR}/${name}.log" || echo "  (no chat lines captured)"
done

# Stable filename in /tmp so cross-RTI diff is one fixed command.
mkdir -p /tmp/hla-traces
cp "${LOG_DIR}/alice.trace" /tmp/hla-traces/alice.gorti.trace 2>/dev/null || true
cp "${LOG_DIR}/bob.trace"   /tmp/hla-traces/bob.gorti.trace   2>/dev/null || true

echo
echo "-- traces -------------------------------------------------------"
echo "  per-federate:  ${LOG_DIR}/{alice,bob}.trace"
echo "  conformance:   /tmp/hla-traces/{alice,bob}.gorti.trace"
echo "  if chat_pitch/run_demo.sh has also run, compare:"
echo "    examples/hla/diff_traces.sh"
echo
echo "-- done. full logs in ${LOG_DIR} --"
