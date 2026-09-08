#!/usr/bin/env bash
# Compare every case (or every case's given variant) whose run has produced
# a NODE.001_01, and print a summary. Does not stop at the first failure.
#
# Usage: ./compare_all.sh [--variant <tag>] [--against <tag>] [-- diff_NODE options]
set -uo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

variant=""
against=""
while [ $# -gt 0 ]; do
    case "$1" in
        --variant) variant="$2"; shift 2 ;;
        --against) against="$2"; shift 2 ;;
        --) break ;;
        *) break ;;
    esac
done

pass_args=()
[ -n "$variant" ] && pass_args+=(--variant "$variant")
[ -n "$against" ] && pass_args+=(--against "$against")

source "$here/lib/run_paths.sh"

failed=0
skipped=0
for case_dir in "$here"/cases/*/; do
    case_name="$(basename "$case_dir")"
    run_id="$case_name"
    [ -n "$variant" ] && run_id="${case_name}__${variant}"

    node="$(rp_node "$run_id")"
    if [ ! -f "$node" ]; then
        echo "SKIP  [$run_id]  -- no NODE.001_01 at $node yet"
        skipped=$((skipped + 1))
        continue
    fi
    "$here/compare_test.sh" "$case_name" "${pass_args[@]+"${pass_args[@]}"}" "$@" || failed=$((failed + 1))
    echo
done

echo "=== summary: $failed failed, $skipped skipped ==="
[ "$failed" -eq 0 ]
