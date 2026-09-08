#!/usr/bin/env bash
# Launch one repro_test case, optionally overriding a param_Eclis variable
# (e.g. to test a new executable while keeping everything else fixed),
# wait for the resulting NODE.001_01 to be written and stop changing, fetch
# it locally, and compare it against the case's reference.
#
# Usage:
#   ./run_test.sh <case_name> [--variant <tag>] [--set KEY=VALUE ...] \
#       [--no-wait] [--poll-interval SEC] [--timeout SEC] [-- extra param_Eclis args]
#
#   --variant <tag>      Run under EXPID "<case_name>__<tag>" instead of
#                         "<case_name>", so it doesn't collide with the
#                         baseline run on the cluster. Use when overriding
#                         something with --set.
#   --set KEY=VALUE      Patch the `KEY=...` assignment line in param_Eclis
#                         (e.g. --set pack=/home/.../arome_v7.5.../) before
#                         launching. Repeatable.
#   --no-wait            Just submit and return (old behaviour): print where
#                         to fetch NODE.001_01 from instead of waiting for it.
#   --poll-interval SEC  How often to check NODE.001_01 (default 20).
#   --timeout SEC        Give up waiting after this long (default 7200 = 2h).
#
# Examples:
#   ./run_test.sh NFR25_standard_namelist
#   ./run_test.sh NFR25_standard_namelist --variant v7.5 \
#       --set pack=/home/gmgec/mrgo/lenobler/packs/arome_v7.5.IMPIIFC2302DP.y/
#
# Copies cases/<case_name>/launch/ into .runs/<run_id>/ (run_id's basename
# becomes EXPID, see param_Eclis) and launches param_Eclis from there.
# param_Eclis's own (very verbose) installer output is redirected to
# results/<run_id>/launch.log instead of the terminal.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ $# -lt 1 ]; then
    echo "Usage: $0 <case_name> [--variant <tag>] [--set KEY=VALUE ...] [--no-wait] [--poll-interval SEC] [--timeout SEC] [-- extra param_Eclis args]" >&2
    exit 1
fi
case_name="$1"; shift

variant=""
overrides=()
no_wait=false
poll_interval=20
timeout=7200
while [ $# -gt 0 ]; do
    case "$1" in
        --variant) variant="$2"; shift 2 ;;
        --set) overrides+=("$2"); shift 2 ;;
        --no-wait) no_wait=true; shift ;;
        --poll-interval) poll_interval="$2"; shift 2 ;;
        --timeout) timeout="$2"; shift 2 ;;
        --) shift; break ;;
        *) break ;;
    esac
done

case_dir="$here/cases/$case_name"
launch_src="$case_dir/launch"
[ -d "$launch_src" ] || { echo "No such case: $case_name (expected $launch_src)" >&2; exit 1; }

run_id="$case_name"
[ -n "$variant" ] && run_id="${case_name}__${variant}"

run_dir="$here/.runs/$run_id"
rm -rf "$run_dir"
mkdir -p "$(dirname "$run_dir")"
cp -r "$launch_src" "$run_dir"

for kv in "${overrides[@]+"${overrides[@]}"}"; do
    key="${kv%%=*}"
    value="${kv#*=}"
    if ! grep -q "^${key}=" "$run_dir/param_Eclis"; then
        echo "Warning: no '${key}=...' line found in param_Eclis to override" >&2
    fi
    # Use '|' as sed delimiter since paths contain '/'.
    sed -i "s|^${key}=.*|${key}=${value}|" "$run_dir/param_Eclis"
    echo ">>> Override: ${key}=${value}"
done

result_dir="$here/results/$run_id"
mkdir -p "$result_dir"
launch_log="$result_dir/launch.log"

echo ">>> Case '$case_name'${variant:+ (variant: $variant)}: launching from $run_dir (EXPID=$run_id)"
echo ">>> param_Eclis output -> $launch_log"
cd "$run_dir"

# if ! yes | ./param_Eclis "$@" >"$launch_log" 2>&1; then
    # echo "!!! param_Eclis exited with an error -- tail of $launch_log:" >&2
    # tail -n 30 "$launch_log" >&2
    # exit 1
# fi
# launch_eclis

echo ">>> Submitted."

node_src="$HOME/relances/TEST_SUITE/$run_id/rundir/NODE.001_01"

if [ "$no_wait" = true ]; then
    echo ">>> --no-wait given. Once the job has finished, fetch:"
    echo "    $node_src"
    echo ">>> into:"
    echo "    $result_dir/NODE.001_01"
    if [ -n "$variant" ]; then
        echo ">>> then run: $here/compare_test.sh $case_name --variant $variant"
    else
        echo ">>> then run: $here/compare_test.sh $case_name"
    fi
    exit 0
fi

echo ">>> Waiting for $node_src to appear (poll every ${poll_interval}s, timeout ${timeout}s)..."
waited=0
while [ ! -f "$node_src" ]; do
    if [ "$waited" -ge "$timeout" ]; then
        echo "!!! Timed out after ${timeout}s waiting for $node_src to appear." >&2
        exit 1
    fi
    sleep "$poll_interval"
    waited=$((waited + poll_interval))
done

echo ">>> $node_src appeared, waiting for it to stop changing..."
prev_stamp=""
stable_checks=0
required_stable=3   # 3 consecutive unchanged polls before considering it done
while [ "$stable_checks" -lt "$required_stable" ]; do
    if [ "$waited" -ge "$timeout" ]; then
        echo "!!! Timed out after ${timeout}s waiting for $node_src to stabilize." >&2
        exit 1
    fi
    sleep "$poll_interval"
    waited=$((waited + poll_interval))
    stamp="$(stat -c '%Y %s' "$node_src" 2>/dev/null || echo "")"
    if [ -n "$stamp" ] && [ "$stamp" = "$prev_stamp" ]; then
        stable_checks=$((stable_checks + 1))
    else
        stable_checks=0
    fi
    prev_stamp="$stamp"
done

cp "$node_src" "$result_dir/NODE.001_01"
echo ">>> Fetched: $result_dir/NODE.001_01"

compare_args=("$case_name")
[ -n "$variant" ] && compare_args+=(--variant "$variant")
"$here/compare_test.sh" "${compare_args[@]}"
