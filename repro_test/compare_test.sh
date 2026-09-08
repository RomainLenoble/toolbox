#!/usr/bin/env bash
# Compare one case's (or one variant's) run outputs against the case's
# stored references -- or, with --against, against another run of the same
# case (a bit-reproducibility check). Covers the NODE.001_01 log always,
# plus -- when the case has a cases/<name>/netcdf_vars and/or
# cases/<name>/fa_grib_files list -- its netCDF and FA/GRIB outputs
# (delegating to compare_netcdf.sh / compare_fa_grib.sh).
#
# The run's outputs are read *in place* from where the job wrote them
# (see lib/run_paths.sh) -- nothing is copied locally. Only the diff
# reports land under results/<run_id>/. Run this on a host that can see
# the run tree (or set $REPRO_RUN_BASE to a mount of it).
#
# Usage: ./compare_test.sh <case_name> [--variant <tag>] [--against <tag>] [run_NODE_path] [-- diff_NODE options]
#   --variant <tag>   which run's outputs to check (run_id "<case>__<tag>";
#                      omitted = "<case>").
#   --against <tag2>  compare against run "<case>__<tag2>" instead of the
#                      stored reference, and demand *bit-exact* agreement
#                      (diff_NODE --rtol 0 --atol 0 --atol-frac 0 --gpnorms '*',
#                      diff_netcdf/diff_fa_grib --rel-max-diff 0). Use to
#                      check a new executable reproduces itself run-to-run.
#                      cases/<name>/node_diff_args is skipped in this mode.
#   run_NODE_path     override the run's NODE.001_01 path (default: live).
#   after "--"        extra options for diff_NODE only (e.g. --rtol 1e-3,
#                      --max-nstep 12); the netCDF / FA-GRIB diffs run with
#                      their defaults (call those scripts directly to tune).
#
# A --variant is otherwise compared against the SAME reference as its base
# case -- the point of a variant (e.g. a new executable via run_test.sh
# --set) is to check it still matches the known-good result.
#
# Exit: 0 if everything agrees, 1 if any comparison FAILs, 2 if none FAILed
# but some comparison could not run.
set -uo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ $# -lt 1 ]; then
    echo "Usage: $0 <case_name> [--variant <tag>] [--against <tag>] [run_NODE_path] [-- diff_NODE options]" >&2
    exit 1
fi
case_name="$1"; shift

variant=""
against=""
while [ $# -gt 0 ]; do
    case "$1" in
        --variant) variant="$2"; shift 2 ;;
        --against) against="$2"; shift 2 ;;
        --) break ;;
        --*) break ;;
        *) break ;;
    esac
done

run_id="$case_name"
[ -n "$variant" ] && run_id="${case_name}__${variant}"
label="$case_name"
[ -n "$variant" ] && label="$case_name (variant: $variant)"

against_run_id=""
if [ -n "$against" ]; then
    against_run_id="${case_name}__${against}"
    label="$label  [repro: vs $against]"
fi

source "$here/lib/run_paths.sh"

result="$(rp_node "$run_id")"
if [ $# -gt 0 ] && [ "$1" != "--" ]; then
    result="$1"; shift
fi
[ "${1:-}" = "--" ] && shift

# what we diff the run against
if [ -n "$against_run_id" ]; then
    ref="$(rp_node "$against_run_id")"
    [ -f "$ref" ] || { echo "Missing run NODE.001_01 for --against: $ref" >&2; exit 1; }
else
    ref="$here/references/$case_name/NODE.001_01"
    [ -f "$ref" ] || { echo "Missing reference log: $ref" >&2; exit 1; }
fi
[ -f "$result" ] || { echo "Missing run NODE.001_01: $result" >&2; echo "(is the job finished? are you on the right host? or pass its path as an argument)" >&2; exit 1; }

# diff_NODE args:
#   - reference mode: per-case cases/<case>/node_diff_args (tuned tolerances)
#   - --against mode: bit-exact, compare everything; node_diff_args skipped
extra_args=()
if [ -n "$against" ]; then
    extra_args=(--rtol 0 --atol 0 --atol-frac 0 --gpnorms '*')
else
    args_file="$here/cases/$case_name/node_diff_args"
    if [ -f "$args_file" ]; then
        while IFS= read -r tok; do
            [ -n "$tok" ] && extra_args+=("$tok")
        done < <(sed 's/#.*//' "$args_file" | xargs -n1 2>/dev/null || true)
    fi
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

# forwarded to the netCDF / FA-GRIB sub-comparisons
sub_args=()
[ -n "$variant" ] && sub_args+=(--variant "$variant")
[ -n "$against" ] && sub_args+=(--against "$against")

# --- netCDF outputs -------------------------------------------------------
if [ -f "$here/cases/$case_name/netcdf_vars" ]; then
    echo
    "$here/compare_netcdf.sh" "$case_name" "${sub_args[@]+"${sub_args[@]}"}"
    case "$?" in
        0) : ;;
        1) any_fail=1 ;;
        *) any_error=1 ;;
    esac
fi

# --- FA / GRIB outputs ---------------------------------------------------
if [ -f "$here/cases/$case_name/fa_grib_files" ]; then
    echo
    "$here/compare_fa_grib.sh" "$case_name" "${sub_args[@]+"${sub_args[@]}"}"
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
echo "PASS  [$label]  -- all comparisons agree"
