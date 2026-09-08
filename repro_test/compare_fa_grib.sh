#!/usr/bin/env bash
# Compare a case's (or variant's) configured FA / GRIB outputs against their
# stored references, field-by-field, using bin/diff_fa_grib (epygram).
#
# Usage: ./compare_fa_grib.sh <case_name> [--variant <tag>] [-- diff_fa_grib options]
#
# Which files to compare come from cases/<case_name>/fa_grib_files (one
# output filename per line, "#" comments allowed), e.g.
#   ICMSHNFR2+0001
#   PFNFR2000+0003.grib
# The reference for each lives at references/<case_name>/fa_grib/<filename>
# and the fresh run's copy at results/<run_id>/fa_grib/<filename>
# (fetch it there yourself, same as the NODE.001_01 / netcdf flow).
#
# Unlike netcdf_vars (one field per file), each entry here is a whole FA/GRIB
# file and diff_fa_grib iterates over every field inside it.
set -uo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ $# -lt 1 ]; then
    echo "Usage: $0 <case_name> [--variant <tag>] [-- diff_fa_grib options]" >&2
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

files_list="$here/cases/$case_name/fa_grib_files"
if [ ! -f "$files_list" ]; then
    echo "No fa_grib_files list for case '$case_name' (expected $files_list) -- nothing to compare." >&2
    exit 1
fi

[ "${1:-}" = "--" ] && shift

out_dir="$here/results/$run_id/fa_grib"
mkdir -p "$out_dir"

failed=0
compared=0
while IFS= read -r fname; do
    fname="${fname%%#*}"                     # strip trailing comments
    fname="$(echo -n "$fname" | xargs)"      # trim whitespace
    [ -z "$fname" ] && continue
    compared=1

    ref="$here/references/$case_name/fa_grib/$fname"
    exp="$out_dir/$fname"
    if [ ! -f "$ref" ]; then
        echo "???  [$label / $fname]  -- no reference at $ref (see save_reference.sh)"
        failed=1
        continue
    fi
    if [ ! -f "$exp" ]; then
        echo "???  [$label / $fname]  -- no fetched file at $exp"
        failed=1
        continue
    fi

    out="$out_dir/diff_${fname}_$(date +%Y%m%dT%H%M%S).txt"
    "$here/bin/diff_fa_grib" "$ref" "$exp" "$@" | tee "$out"
    rc="${PIPESTATUS[0]}"
    if [ "$rc" -eq 0 ]; then
        echo "PASS  [$label / $fname]"
    else
        echo "FAIL  [$label / $fname]  -- see $out"
        failed=1
    fi
    echo
done < "$files_list"

[ "$compared" -eq 1 ] || echo "Nothing was compared -- is $files_list empty?"
exit "$failed"
