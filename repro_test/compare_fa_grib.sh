#!/usr/bin/env bash
# Compare a case's (or variant's) configured FA / GRIB outputs against their
# stored references, field-by-field, using bin/diff_fa_grib (epygram) --
# or, with --against, against another run.
#
# Usage: ./compare_fa_grib.sh <case_name> [--variant <tag>] [--against <tag>] [-- diff_fa_grib options]
#
# Which files to compare come from cases/<case_name>/fa_grib_files (one
# output filename per line, "#" comments allowed), e.g.
#   ICMSHNFR2+0001
#   PFNFR2000+0003.grib
# Each file is read in place from the run's rundir (same dir as NODE.001_01,
# see lib/run_paths.sh).
#
#   default          -> diff against references/<case_name>/fa_grib/<filename>
#   --against <tag2> -> diff against run "<case_name>__<tag2>" (bit-exact:
#                        --rel-max-diff 0), for a reproducibility check
#
# Unlike netcdf_vars (one field per file), each entry here is a whole FA/GRIB
# file and diff_fa_grib iterates over every field inside it.
set -uo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ $# -lt 1 ]; then
    echo "Usage: $0 <case_name> [--variant <tag>] [--against <tag>] [-- diff_fa_grib options]" >&2
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

files_list="$here/cases/$case_name/fa_grib_files"
if [ ! -f "$files_list" ]; then
    echo "No fa_grib_files list for case '$case_name' (expected $files_list) -- nothing to compare." >&2
    exit 1
fi

source "$here/lib/run_paths.sh"

# in --against (repro) mode, demand bit-exact agreement unless overridden
diff_defaults=()
[ -n "$against" ] && diff_defaults=(--rel-max-diff 0)

# only the diff reports are written locally; the run's FA/GRIB is read in place
out_dir="$here/results/$run_id/fa_grib"
mkdir -p "$out_dir"

failed=0
missing=0
compared=0
while IFS= read -r fname; do
    fname="${fname%%#*}"                     # strip trailing comments
    fname="$(echo -n "$fname" | xargs)"      # trim whitespace
    [ -z "$fname" ] && continue
    compared=1

    if [ -n "$against_run_id" ]; then
        ref="$(rp_fa_grib "$against_run_id" "$fname")"
        ref_what="run $against_run_id"
    else
        ref="$here/references/$case_name/fa_grib/$fname"
        ref_what="reference"
    fi
    exp="$(rp_fa_grib "$run_id" "$fname")"
    if [ ! -f "$ref" ]; then
        echo "???  [$label / $fname]  -- no $ref_what at $ref"
        missing=1
        continue
    fi
    if [ ! -f "$exp" ]; then
        echo "???  [$label / $fname]  -- no run output at $exp (job finished? right host?)"
        missing=1
        continue
    fi

    out="$out_dir/diff_${fname}_$(date +%Y%m%dT%H%M%S).txt"
    "$here/bin/diff_fa_grib" "$ref" "$exp" "${diff_defaults[@]+"${diff_defaults[@]}"}" "$@" | tee "$out"
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
if [ "$failed" -eq 1 ]; then exit 1; fi
if [ "$missing" -eq 1 ] || [ "$compared" -eq 0 ]; then exit 2; fi
exit 0
