#!/usr/bin/env bash
# Compare a case's (or variant's) configured netCDF outputs against their
# stored references.
#
# Usage: ./compare_netcdf.sh <case_name> [--variant <tag>] [-- diff_netcdf options]
#
# Which files to compare come from cases/<case_name>/netcdf_vars (one field
# tag per line, e.g. "hour_zg", "#" comments allowed) -- see run_test.sh for
# how those get fetched from iox_keep/ in the first place.
set -uo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ $# -lt 1 ]; then
    echo "Usage: $0 <case_name> [--variant <tag>] [-- diff_netcdf options]" >&2
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

vars_file="$here/cases/$case_name/netcdf_vars"
if [ ! -f "$vars_file" ]; then
    echo "No netcdf_vars file for case '$case_name' (expected $vars_file) -- nothing to compare." >&2
    exit 1
fi

out_dir="$here/results/$run_id/netcdf"
mkdir -p "$out_dir"

failed=0
compared=0
while IFS= read -r tag; do
    tag="${tag%%#*}"                      # strip trailing comments
    tag="$(echo -n "$tag" | xargs)"       # trim whitespace
    [ -z "$tag" ] && continue
    compared=1

    ref="$here/references/$case_name/netcdf/$tag.nc"
    exp="$out_dir/$tag.nc"
    if [ ! -f "$ref" ]; then
        echo "??? [$label / $tag]  -- no reference at $ref (see save_reference.sh)"
        failed=1
        continue
    fi
    if [ ! -f "$exp" ]; then
        echo "??? [$label / $tag]  -- no fetched file at $exp"
        failed=1
        continue
    fi

    out="$out_dir/diff_${tag}_$(date +%Y%m%dT%H%M%S).txt"
    "$here/bin/diff_netcdf" "$ref" "$exp" "$@" | tee "$out"
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
exit "$failed"
