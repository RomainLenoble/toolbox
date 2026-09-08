#!/usr/bin/env bash
# Promote a run's fetched output (results/<run_id>/...) into a case's
# stored reference (references/<case_name>/...). Use this once, on a run
# you trust, to establish or update what future runs of that case get
# checked against -- typically a baseline run (no --variant).
#
# Usage: ./save_reference.sh <case_name> [--from-variant <tag>]
#
# Copies results/<run_id>/NODE.001_01 -> references/<case_name>/NODE.001_01
# and, if cases/<case_name>/netcdf_vars exists, every configured
# results/<run_id>/netcdf/<tag>.nc -> references/<case_name>/netcdf/<tag>.nc
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ $# -lt 1 ]; then
    echo "Usage: $0 <case_name> [--from-variant <tag>]" >&2
    exit 1
fi
case_name="$1"; shift

from_variant=""
if [ "${1:-}" = "--from-variant" ]; then
    from_variant="$2"; shift 2
fi
run_id="$case_name"
[ -n "$from_variant" ] && run_id="${case_name}__${from_variant}"

result_dir="$here/results/$run_id"
node_src="$result_dir/NODE.001_01"
[ -f "$node_src" ] || { echo "No $node_src to promote (run this case first)." >&2; exit 1; }

ref_dir="$here/references/$case_name"
mkdir -p "$ref_dir"
cp "$node_src" "$ref_dir/NODE.001_01"
echo ">>> Saved reference: $ref_dir/NODE.001_01  (from $node_src)"

netcdf_vars_file="$here/cases/$case_name/netcdf_vars"
if [ -f "$netcdf_vars_file" ]; then
    mkdir -p "$ref_dir/netcdf"
    while IFS= read -r tag; do
        tag="$(echo -n "${tag%%#*}" | xargs)"
        [ -z "$tag" ] && continue
        src="$result_dir/netcdf/$tag.nc"
        if [ -f "$src" ]; then
            cp "$src" "$ref_dir/netcdf/$tag.nc"
            echo ">>> Saved reference: $ref_dir/netcdf/$tag.nc  (from $src)"
        else
            echo "Warning: no $src to promote for '$tag' -- skipped." >&2
        fi
    done < "$netcdf_vars_file"
fi

fa_grib_files_file="$here/cases/$case_name/fa_grib_files"
if [ -f "$fa_grib_files_file" ]; then
    mkdir -p "$ref_dir/fa_grib"
    while IFS= read -r fname; do
        fname="$(echo -n "${fname%%#*}" | xargs)"
        [ -z "$fname" ] && continue
        src="$result_dir/fa_grib/$fname"
        if [ -f "$src" ]; then
            cp "$src" "$ref_dir/fa_grib/$fname"
            echo ">>> Saved reference: $ref_dir/fa_grib/$fname  (from $src)"
        else
            echo "Warning: no $src to promote for '$fname' -- skipped." >&2
        fi
    done < "$fa_grib_files_file"
fi
