#!/usr/bin/env bash
# Launch every case under cases/, optionally with the same override applied
# to all of them (e.g. testing a new executable across every case).
#
# Usage: ./run_all.sh [--variant <tag>] [--set KEY=VALUE ...] [--repro] [-- extra param_Eclis args]
#
# See run_test.sh for what --variant/--set/--repro do. A non-zero result
# from one case (FAIL / couldn't compare) doesn't stop the rest; the count
# is reported at the end.
set -uo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

failed=0
for case_dir in "$here"/cases/*/; do
    case_name="$(basename "$case_dir")"
    "$here/run_test.sh" "$case_name" "$@" || failed=$((failed + 1))
    echo
done

echo "=== run_all: $failed case(s) reported a non-zero result ==="
[ "$failed" -eq 0 ]
