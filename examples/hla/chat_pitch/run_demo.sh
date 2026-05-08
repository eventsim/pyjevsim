#!/usr/bin/env bash
# Orchestrate the Pitch RTI two-federate chat demo.
#
# Spawns two kdx-rti gateway processes (disjoint port triples) and two
# pyjevsim federates (alice, bob), waits for them to finish, prints the
# combined output. Pitch CRC must already be running on its standard
# port — start it manually with $PRTI1516E_HOME/prti1516e first.
#
# Usage:
#     ./run_demo.sh                    # default: 5 messages each, 10s sim
#     COUNT=3 PERIOD=0.5 END=8 ./run_demo.sh
#     KDX_RTI_DIR=/path/to/kdx-rti ./run_demo.sh
#
# Requirements:
#   - $PRTI1516E_HOME exported, pRTI's CRC running
#   - kdx-rti repo built (mvn -f $KDX_RTI_DIR/pom.xml package)
#   - pyjevsim + kdx_rti pip-installed in the active Python env
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
KDX_RTI_DIR="${KDX_RTI_DIR:-${REPO_ROOT}/../kdx-rti}"
COUNT="${COUNT:-5}"
PERIOD="${PERIOD:-1.0}"
END="${END:-10.0}"
LOOKAHEAD="${LOOKAHEAD:-0.1}"

if [[ ! -x "${KDX_RTI_DIR}/run-gateway.sh" ]]; then
    echo "FATAL: kdx-rti gateway launcher not found at ${KDX_RTI_DIR}/run-gateway.sh"
    echo "  set KDX_RTI_DIR=<path-to-kdx-rti-repo> and rebuild the shaded jar"
    exit 2
fi
if ! python3 -c "import kdx_rti" 2>/dev/null; then
    echo "FATAL: 'kdx_rti' python package is not installed in this venv"
    echo "  pip install -e ${KDX_RTI_DIR}/python"
    exit 2
fi
if [[ -z "${PRTI1516E_HOME:-}" ]]; then
    echo "WARN: PRTI1516E_HOME is not set — gateways may fail to load Pitch LRC"
fi

LOG_DIR="$(mktemp -d -t hla-chat-pitch.XXXXXX)"
echo "log dir: ${LOG_DIR}"

# Track child PIDs for clean shutdown.
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

start_gateway() {
    local label="$1"; shift
    local script="$1"; shift
    local logfile="${LOG_DIR}/${label}.log"
    echo "starting ${label}: ${script}  (log: ${logfile})"
    ( cd "${KDX_RTI_DIR}" && bash "${script}" >"${logfile}" 2>&1 ) &
    PIDS+=("$!")
}

start_federate() {
    local name="$1"; shift
    local ports="$1"; shift
    local logfile="${LOG_DIR}/${name}.log"
    echo "starting federate ${name} (ports=${ports})  (log: ${logfile})"
    ( cd "${REPO_ROOT}" && python3 -m examples.hla.chat_pitch.run "${name}" \
        --ports "${ports}" --count "${COUNT}" --period "${PERIOD}" \
        --end "${END}" --log INFO >"${logfile}" 2>&1 ) &
    PIDS+=("$!")
}

start_gateway alice-gw run-gateway.sh
start_gateway bob-gw   run-gateway-bob.sh

# Give the gateways a moment to bind their ZMQ sockets and connect to pRTI.
sleep 2

start_federate alice 5555,5556,5557
start_federate bob   5558,5559,5560

# Wait for both federates to finish; ignore their exit codes here so
# we always run the cleanup trap.
wait "${PIDS[2]}" "${PIDS[3]}" || true

echo
echo "-- federate output ----------------------------------------------"
for name in alice bob; do
    echo "## ${name}.log"
    grep -E '\[(alice|bob)\] heard' "${LOG_DIR}/${name}.log" || echo "  (no chat lines captured)"
done
echo "-- done. full logs in ${LOG_DIR} --"
