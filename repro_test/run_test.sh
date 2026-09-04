#!/usr/bin/env bash
# Launch one repro_test case, optionally overriding a param_Eclis variable
# (e.g. to test a new executable while keeping everything else fixed).
#
# Usage:
#   ./run_test.sh <case_name> [--variant <tag>] [--set KEY=VALUE ...] [-- extra param_Eclis args]
#
#   --variant <tag>     Run under EXPID "<case_name>__<tag>" instead of
#                        "<case_name>", so it doesn't collide with the
#                        baseline run on the cluster. Use when overriding
#                        something with --set.
#   --set KEY=VALUE     Patch the `KEY=...` assignment line in param_Eclis
#                        (e.g. --set pack=/home/.../arome_v7.5.../) before
#                        launching. Repeatable.
#
# Examples:
#   ./run_test.sh NFR25_standard_namelist
#   ./run_test.sh NFR25_standard_namelist --variant v7.5 \
#       --set pack=/home/gmgec/mrgo/lenobler/packs/arome_v7.5.IMPIIFC2302DP.y/
#
# Copies cases/<case_name>/launch/ into .runs/<run_id>/ (run_id's basename
# becomes EXPID, see param_Eclis) and launches param_Eclis from there. The
# job itself is submitted asynchronously to the cluster; this script does
# not wait for it.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ $# -lt 1 ]; then
    echo "Usage: $0 <case_name> [--variant <tag>] [--set KEY=VALUE ...] [-- extra param_Eclis args]" >&2
    exit 1
fi
case_name="$1"; shift

variant=""
overrides=()
while [ $# -gt 0 ]; do
    case "$1" in
        --variant) variant="$2"; shift 2 ;;
        --set) overrides+=("$2"); shift 2 ;;
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

echo ">>> Case '$case_name'${variant:+ (variant: $variant)}: launching from $run_dir (EXPID=$(basename "$run_dir"))"
cd "$run_dir"
./param_Eclis "$@"

result_dir="$here/results/$run_id"
echo ">>> Once the job has finished, copy its NODE.001_01 into:"
echo "    $result_dir/NODE.001_01"
if [ -n "$variant" ]; then
    echo ">>> then run: $here/compare_test.sh $case_name --variant $variant"
else
    echo ">>> then run: $here/compare_test.sh $case_name"
fi
