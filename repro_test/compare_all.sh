#!/usr/bin/env bash
# Compare every case (or every case's given variant) that has a fresh
# results/.../NODE.001_01 waiting, and print a summary. Does not stop at
# the first failure.
#
# Usage: ./compare_all.sh [--variant <tag>] [-- diff_NODE options]
set -uo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

variant=""
if [ "${1:-}" = "--variant" ]; then
    variant="$2"; shift 2
fi

failed=0
skipped=0
for case_dir in "$here"/cases/*/; do
    case_name="$(basename "$case_dir")"
    run_id="$case_name"
    [ -n "$variant" ] && run_id="${case_name}__${variant}"

    if [ ! -f "$here/results/$run_id/NODE.001_01" ]; then
        echo "SKIP  [$run_id]  -- no results/$run_id/NODE.001_01 yet"
        skipped=$((skipped + 1))
        continue
    fi
    if [ -n "$variant" ]; then
        "$here/compare_test.sh" "$case_name" --variant "$variant" "$@" || failed=$((failed + 1))
    else
        "$here/compare_test.sh" "$case_name" "$@" || failed=$((failed + 1))
    fi
    echo
done

echo "=== summary: $failed failed, $skipped skipped ==="
[ "$failed" -eq 0 ]
