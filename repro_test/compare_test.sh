#!/usr/bin/env bash
# Compare one case's (or one variant's) fresh outputs against the case's
# stored references: the NODE.001_01 log always, plus -- when the case has
# a cases/<name>/netcdf_vars and/or cases/<name>/fa_grib_files list -- its
# netCDF and FA/GRIB outputs (delegating to compare_netcdf.sh /
# compare_fa_grib.sh).
#
# Usage: ./compare_test.sh <case_name> [--variant <tag>] [fresh_NODE_path] [-- diff_NODE options]
#   - a variant always compares against the SAME reference as its base case
#     (references/<case_name>/NODE.001_01) -- the point of a variant (e.g. a
#     new executable via run_test.sh --set) is to check it still matches
#     the case's existing reference, not to set a new one.
#   - if fresh_NODE_path is omitted, defaults to results/<run_id>/NODE.001_01
#     (run_id = "<case_name>", or "<case_name>__<tag>" with --variant)
#   - extra options after "--" go to diff_NODE only (e.g. --rtol 1e-3,
#     --max-nstep 12); the netCDF / FA-GRIB diffs run with their defaults
#     (call compare_netcdf.sh / compare_fa_grib.sh directly to tune those)
#
# Exit: 0 if everything is within tolerance, 1 if any comparison FAILs,
# 2 if none FAILed but some comparison could not run.
set -uo pipefail

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

# Per-case extra diff_NODE args (e.g. a tighter --rtol, a --preset, a
# --fields-from), from cases/<case>/node_diff_args if present. Whitespace-
# separated tokens, quotes respected, '#' starts a comment. e.g.:
#     --preset arome-lam
#     --rtol 1e-8 --max-nstep 12
#     --spnorms "VORTICITY,DIVERGENCE,TEMPERATURE,KINETIC ENERGY"
extra_args=()
args_file="$here/cases/$case_name/node_diff_args"
if [ -f "$args_file" ]; then
    while IFS= read -r tok; do
        [ -n "$tok" ] && extra_args+=("$tok")
    done < <(sed 's/#.*//' "$args_file" | xargs -n1 2>/dev/null || true)
fi

out_dir="$here/results/$run_id"
mkdir -p "$out_dir"
out="$out_dir/diff_$(date +%Y%m%dT%H%M%S).txt"

any_fail=0
any_error=0

# --- NODE.001_01 -----------------------------------------------------------
"$here/bin/diff_NODE" "$ref" "$result" "${extra_args[@]+"${extra_args[@]}"}" "$@" | tee "$out"
rc="${PIPESTATUS[0]}"
case "$rc" in
    0) echo "PASS  [$label / NODE]" ;;
    1) echo "FAIL  [$label / NODE]  -- see $out"; any_fail=1 ;;
    *) echo "???   [$label / NODE]  -- diff_NODE could not compare (rc=$rc, see $out)"; any_error=1 ;;
esac

variant_args=()
[ -n "$variant" ] && variant_args=(--variant "$variant")

# --- netCDF outputs -------------------------------------------------------
if [ -f "$here/cases/$case_name/netcdf_vars" ]; then
    echo
    "$here/compare_netcdf.sh" "$case_name" "${variant_args[@]+"${variant_args[@]}"}"
    case "$?" in
        0) : ;;
        1) any_fail=1 ;;
        *) any_error=1 ;;
    esac
fi

# --- FA / GRIB outputs ---------------------------------------------------
if [ -f "$here/cases/$case_name/fa_grib_files" ]; then
    echo
    "$here/compare_fa_grib.sh" "$case_name" "${variant_args[@]+"${variant_args[@]}"}"
    case "$?" in
        0) : ;;
        1) any_fail=1 ;;
        *) any_error=1 ;;
    esac
fi

echo
if [ "$any_fail" -eq 1 ]; then
    echo "FAIL  [$label]  -- one or more comparisons out of tolerance"
    exit 1
elif [ "$any_error" -eq 1 ]; then
    echo "???   [$label]  -- one or more comparisons could not run"
    exit 2
fi
echo "PASS  [$label]  -- all comparisons within tolerance"
