#!/usr/bin/env bash
# Launch one repro_test case, optionally overriding a param_Eclis variable
# (e.g. to test a new executable while keeping everything else fixed),
# wait for the resulting NODE.001_01 to be written and stop changing, then
# compare the run's outputs (in place, not copied) against the case's
# references via compare_test.sh.
#
# Usage:
#   ./run_test.sh <case_name> [--variant <tag>] [--set KEY=VALUE ...] \
#       [--repro] [--repro-set KEY=VALUE ...] [--no-compare] \
#       [--no-wait] [--poll-interval SEC] [--timeout SEC] [-- extra param_Eclis args]
#
#   --variant <tag>      Run under EXPID "<case_name>__<tag>" instead of
#                         "<case_name>", so it doesn't collide with the
#                         baseline run on the cluster. Use when overriding
#                         something with --set. Required with --repro.
#   --set KEY=VALUE      Patch the `KEY=...` assignment line in param_Eclis
#                         (e.g. --set pack=/home/.../arome_v7.5.../) before
#                         launching. Repeatable.
#   --repro             Also launch a SECOND, identical run under
#                         "<case>__<tag>__rep" and, once both finish, do two
#                         checks:
#                           [1/2] <tag> vs <tag>__rep  -- is the executable
#                                 bit-reproducible run-to-run? (bit-exact)
#                           [2/2] <tag> vs saved reference -- does it still
#                                 match the known-good result? (case tolerances)
#   --repro-set KEY=VALUE  Extra override applied to the __rep run only
#                         (e.g. --repro-set NODE_ARP=3 to also vary the MPI
#                         decomposition -- a stronger reproducibility test).
#                         Repeatable.
#   --no-compare        Submit + wait, but don't run the comparison(s).
#   --no-wait            Just submit and return: print the command(s) to run
#                         once the job(s) have finished.
#   --poll-interval SEC  How often to check NODE.001_01 (default 20).
#   --timeout SEC        Give up waiting after this long (default 7200 = 2h).
#
# Examples:
#   ./run_test.sh NFR25_standard_namelist
#   ./run_test.sh NFR25_standard_namelist --variant v7.5 \
#       --set pack=/home/gmgec/mrgo/lenobler/packs/arome_v7.5.IMPIIFC2302DP.y/ --repro
#
# Copies cases/<case_name>/launch/ into .runs/<run_id>/ (run_id's basename
# becomes EXPID, see param_Eclis) and launches param_Eclis from there.
# param_Eclis's own (very verbose) installer output is redirected to
# results/<run_id>/launch.log instead of the terminal.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ $# -lt 1 ]; then
    echo "Usage: $0 <case_name> [--variant <tag>] [--set KEY=VALUE ...] [--repro] [--repro-set KEY=VALUE ...] [--no-compare] [--no-wait] [--poll-interval SEC] [--timeout SEC] [-- extra param_Eclis args]" >&2
    exit 1
fi
case_name="$1"; shift

variant=""
overrides=()
repro_overrides=()
repro=false
no_compare=false
no_wait=false
poll_interval=20
timeout=7200
while [ $# -gt 0 ]; do
    case "$1" in
        --variant) variant="$2"; shift 2 ;;
        --set) overrides+=("$2"); shift 2 ;;
        --repro) repro=true; shift ;;
        --repro-set) repro_overrides+=("$2"); shift 2 ;;
        --no-compare) no_compare=true; shift ;;
        --no-wait) no_wait=true; shift ;;
        --poll-interval) poll_interval="$2"; shift 2 ;;
        --timeout) timeout="$2"; shift 2 ;;
        --) shift; break ;;
        *) break ;;
    esac
done
extra_launch_args=("$@")

case_dir="$here/cases/$case_name"
launch_src="$case_dir/launch"
[ -d "$launch_src" ] || { echo "No such case: $case_name (expected $launch_src)" >&2; exit 1; }

if [ "$repro" = true ] && [ -z "$variant" ]; then
    echo "--repro needs --variant <tag> (the two runs need distinct EXPIDs)." >&2
    exit 1
fi

run_id="$case_name"
[ -n "$variant" ] && run_id="${case_name}__${variant}"
rep_run_id="${run_id}__rep"

source "$here/lib/run_paths.sh"

# prepare .runs/<run_id>/ from the case's launch/, apply overrides, submit.
# args: <run_id> [extra KEY=VALUE ...]
prepare_and_submit() {
    local rid="$1"; shift
    local extra=( "$@" )
    local rdir="$here/.runs/$rid"
    rm -rf "$rdir"
    mkdir -p "$(dirname "$rdir")"
    cp -r "$launch_src" "$rdir"

    local kv key value
    for kv in "${overrides[@]+"${overrides[@]}"}" "${extra[@]+"${extra[@]}"}"; do
        key="${kv%%=*}"
        value="${kv#*=}"
        if ! grep -q "^${key}=" "$rdir/param_Eclis"; then
            echo "Warning: no '${key}=...' line found in param_Eclis to override" >&2
        fi
        sed -i "s|^${key}=.*|${key}=${value}|" "$rdir/param_Eclis"   # '|' delim: paths have '/'
        echo ">>> [$rid] override: ${key}=${value}"
    done

    mkdir -p "$here/results/$rid"
    echo ">>> [$rid] launching from $rdir (EXPID=$rid); param_Eclis output -> $here/results/$rid/launch.log"
    (
        cd "$rdir"
        # if ! yes | ./param_Eclis "${extra_launch_args[@]}" >"$here/results/$rid/launch.log" 2>&1; then
        #     echo "!!! param_Eclis exited with an error -- tail of the log:" >&2
        #     tail -n 30 "$here/results/$rid/launch.log" >&2
        #     exit 1
        # fi
        launch_eclis
        :
    )
    echo ">>> [$rid] submitted."
}

# block until <run_id>'s NODE.001_01 exists and has stopped growing
wait_for_node() {
    local rid="$1"
    local node_src; node_src="$(rp_node "$rid")"
    local waited=0

    echo ">>> [$rid] waiting for $node_src (poll ${poll_interval}s, timeout ${timeout}s)..."
    while [ ! -f "$node_src" ]; do
        if [ "$waited" -ge "$timeout" ]; then
            echo "!!! [$rid] timed out waiting for $node_src to appear." >&2
            exit 1
        fi
        sleep "$poll_interval"; waited=$((waited + poll_interval))
    done

    local prev_stamp="" stable_checks=0 required_stable=3
    while [ "$stable_checks" -lt "$required_stable" ]; do
        if [ "$waited" -ge "$timeout" ]; then
            echo "!!! [$rid] timed out waiting for $node_src to stabilize." >&2
            exit 1
        fi
        sleep "$poll_interval"; waited=$((waited + poll_interval))
        local stamp; stamp="$(stat -c '%Y %s' "$node_src" 2>/dev/null || echo "")"
        if [ -n "$stamp" ] && [ "$stamp" = "$prev_stamp" ]; then
            stable_checks=$((stable_checks + 1))
        else
            stable_checks=0
        fi
        prev_stamp="$stamp"
    done
    echo ">>> [$rid] NODE.001_01 ready."
}

# --- submit --------------------------------------------------------------
prepare_and_submit "$run_id"
if [ "$repro" = true ]; then
    prepare_and_submit "$rep_run_id" "${repro_overrides[@]+"${repro_overrides[@]}"}"
fi

if [ "$no_wait" = true ]; then
    v=""; [ -n "$variant" ] && v=" --variant $variant"
    echo
    echo ">>> --no-wait given. Once the job(s) have finished, run:"
    if [ "$repro" = true ]; then
        echo "    $here/compare_test.sh $case_name$v --against ${variant}__rep   # [1/2] bit-reproducibility"
        echo "    $here/compare_test.sh $case_name$v                              # [2/2] vs saved reference"
    else
        echo "    $here/compare_test.sh $case_name$v"
    fi
    exit 0
fi

# --- wait ---------------------------------------------------------------
wait_for_node "$run_id"
if [ "$repro" = true ]; then
    wait_for_node "$rep_run_id"
fi

if [ "$no_compare" = true ]; then
    echo ">>> --no-compare given, done."
    exit 0
fi

# --- compare ----------------------------------------------------------
v_args=()
[ -n "$variant" ] && v_args=(--variant "$variant")

if [ "$repro" = true ]; then
    echo
    echo "======================================================================"
    echo "  [1/2] bit-reproducibility of the executable:  $variant  vs  ${variant}__rep"
    echo "======================================================================"
    rc_repro=0
    "$here/compare_test.sh" "$case_name" "${v_args[@]}" --against "${variant}__rep" || rc_repro=$?

    echo
    echo "======================================================================"
    echo "  [2/2] vs saved reference:  $variant  vs  references/$case_name/"
    echo "======================================================================"
    rc_ref=0
    "$here/compare_test.sh" "$case_name" "${v_args[@]}" || rc_ref=$?

    echo
    echo "=== executable test summary [$case_name / $variant] ==="
    case "$rc_repro" in
        0) echo "  bit-reproducible : PASS" ;;
        1) echo "  bit-reproducible : FAIL  -- the two identical runs differ" ;;
        *) echo "  bit-reproducible : ???   -- could not compare" ;;
    esac
    case "$rc_ref" in
        0) echo "  vs reference     : PASS" ;;
        1) echo "  vs reference     : FAIL  -- differs from the known-good result" ;;
        *) echo "  vs reference     : ???   -- could not compare" ;;
    esac
    if [ "$rc_repro" -eq 0 ] && [ "$rc_ref" -eq 0 ]; then
        exit 0
    elif [ "$rc_repro" -eq 1 ] || [ "$rc_ref" -eq 1 ]; then
        exit 1
    else
        exit 2
    fi
fi

echo
echo ">>> Run finished. Comparing its outputs (in place) against references..."
"$here/compare_test.sh" "$case_name" "${v_args[@]}"
