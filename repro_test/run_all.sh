#!/usr/bin/env bash
# Launch every case under cases/, optionally with the same override applied
# to all of them (e.g. testing a new executable across every case).
#
# Usage: ./run_all.sh [--variant <tag>] [--set KEY=VALUE ...] [-- extra param_Eclis args]
#
# See run_test.sh for what --variant/--set do.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for case_dir in "$here"/cases/*/; do
    case_name="$(basename "$case_dir")"
    "$here/run_test.sh" "$case_name" "$@"
    echo
done
