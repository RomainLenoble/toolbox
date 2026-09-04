#!/usr/bin/env bash
# Compare one case's (or one variant's) fresh NODE.001_01 against the
# case's stored reference.
#
# Usage: ./compare_test.sh <case_name> [--variant <tag>] [fresh_NODE_path] [-- diff_NODE options]
#   - a variant always compares against the SAME reference as its base case
#     (references/<case_name>/NODE.001_01) -- the point of a variant (e.g. a
#     new executable via run_test.sh --set) is to check it still matches
#     the case's existing reference, not to set a new one.
#   - if fresh_NODE_path is omitted, defaults to results/<run_id>/NODE.001_01
#     (run_id = "<case_name>", or "<case_name>__<tag>" with --variant)
#   - extra diff_NODE options (e.g. --norm-max-diff 0.1) can follow after --
#
# diff_NODE always exits 0, so pass/fail here is decided by scanning its
# report for the "WARNING" lines it prints when a norm is outside limits.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ $# -lt 1 ]; then
    echo "Usage: $0 <case_name> [--variant <tag>] [fresh_NODE_path] [-- diff_NODE options]" >&2
    exit 1
fi
case_name="$1"; shift

variant=""
if [ "${1:-}" = "--variant" ]; then
    variant="$2"; shift 2
fi
run_id="$case_name"
[ -n "$variant" ] && run_id="${case_name}__${variant}"
label="$case_name"
[ -n "$variant" ] && label="$case_name (variant: $variant)"

result="$here/results/$run_id/NODE.001_01"
if [ $# -gt 0 ] && [ "$1" != "--" ]; then
    result="$1"; shift
fi
[ "${1:-}" = "--" ] && shift

ref="$here/references/$case_name/NODE.001_01"
[ -f "$ref" ] || { echo "Missing reference log: $ref" >&2; exit 1; }
[ -f "$result" ] || { echo "Missing fresh log: $result" >&2; echo "(copy the run's NODE.001_01 there, or pass its path as an argument)" >&2; exit 1; }

out_dir="$here/results/$run_id"
mkdir -p "$out_dir"
out="$out_dir/diff_$(date +%Y%m%dT%H%M%S).txt"

# diff_NODE's built-in --gpnorms/--spnorms defaults (VORTICITY, U VELOCITY,
# SURFACE PRESSURE, ...) are the global IFS/ARPEGE field names -- AROME LAM
# NODE files don't have those, so with the plain defaults the norms table
# comes out empty and diff_NODE still "passes". --gpnorms '*' below matches
# every GPNORM field actually present instead; override by passing your own
# --gpnorms/--spnorms after "--".
"$here/bin/diff_NODE" "$ref" "$result" --gpnorms '*' "$@" | tee "$out"

norm_lines="$(grep -c "^ NORMDIFF | " "$out" || true)"  # 2 of these are always the table header

if grep -q "WARNING" "$out"; then
    echo "FAIL  [$label]  -- see $out"
    exit 1
elif [ "$norm_lines" -le 2 ]; then
    echo "??? [$label]  -- norms table is empty, nothing was actually compared (see $out)"
    exit 2
else
    echo "PASS  [$label]"
fi
