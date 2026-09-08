#!/usr/bin/env bash
# Compare a case's (or variant's) configured netCDF outputs against their
# stored references -- or, with --against, against another run.
#
# Usage: ./compare_netcdf.sh <case_name> [--variant <tag>] [--against <tag>] [-- diff_netcdf options]
#
# Which files to compare come from cases/<case_name>/netcdf_vars (one field
# tag per line, e.g. "hour_zg", "#" comments allowed). The run's netCDF is
# read in place from its XIOS iox_keep/ dir (see lib/run_paths.sh).
#
#   default          -> diff against references/<case_name>/netcdf/<tag>.nc
#   --against <tag2> -> diff against run "<case_name>__<tag2>" (bit-exact:
#                        --rel-max-diff 0), for a reproducibility check
set -uo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ $# -lt 1 ]; then
    echo "Usage: $0 <case_name> [--variant <tag>] [--against <tag>] [-- diff_netcdf options]" >&2
    exit 1
fi
case_name="$1"; shift

variant=""
against=""
while [ $# -gt 0 ]; do
    case "$1" in
        --variant) variant="$2"; shift 2 ;;
        --against) against="$2"; shift 2 ;;
        --) shift; break ;;
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

vars_file="$here/cases/$case_name/netcdf_vars"
if [ ! -f "$vars_file" ]; then
    echo "No netcdf_vars file for case '$case_name' (expected $vars_file) -- nothing to compare." >&2
    exit 1
fi

source "$here/lib/run_paths.sh"

# in --against (repro) mode, demand bit-exact agreement unless overridden
diff_defaults=()
[ -n "$against" ] && diff_defaults=(--rel-max-diff 0)

# only the diff reports are written locally; the run's netCDF is read in place
out_dir="$here/results/$run_id/netcdf"
mkdir -p "$out_dir"

failed=0
missing=0
compared=0
while IFS= read -r tag; do
    tag="${tag%%#*}"                      # strip trailing comments
    tag="$(echo -n "$tag" | xargs)"       # trim whitespace
    [ -z "$tag" ] && continue
    compared=1

    if [ -n "$against_run_id" ]; then
        ref="$(rp_netcdf "$against_run_id" "$tag")"
        ref_what="run $against_run_id"
    else
        ref="$here/references/$case_name/netcdf/$tag.nc"
        ref_what="reference"
    fi
    exp="$(rp_netcdf "$run_id" "$tag")"
    if [ ! -f "$ref" ]; then
        echo "??? [$label / $tag]  -- no $ref_what at $ref"
        missing=1
        continue
    fi
    if [ ! -f "$exp" ]; then
        echo "??? [$label / $tag]  -- no run output at $exp (job finished? right host?)"
        missing=1
        continue
    fi

    out="$out_dir/diff_${tag}_$(date +%Y%m%dT%H%M%S).txt"
    "$here/bin/diff_netcdf" "$ref" "$exp" "${diff_defaults[@]+"${diff_defaults[@]}"}" "$@" | tee "$out"
    rc="${PIPESTATUS[0]}"
    if [ "$rc" -eq 0 ]; then
        echo "PASS  [$label / $tag]"
    else
        echo "FAIL  [$label / $tag]  -- see $out"
        failed=1
    fi
    echo
done < "$vars_file"

[ "$compared" -eq 1 ] || echo "Nothing was compared -- is $vars_file empty?"
if [ "$failed" -eq 1 ]; then exit 1; fi
if [ "$missing" -eq 1 ] || [ "$compared" -eq 0 ]; then exit 2; fi
exit 0
