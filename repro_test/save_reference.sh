#!/usr/bin/env bash
# Promote a run's live output into a case's stored reference
# (references/<case_name>/...). Use this once, on a run you trust, to
# establish or update what future runs of that case get checked against --
# typically a baseline run (no --variant).
#
# This is the one place a copy happens: the reference has to live in the
# repo. Everything else (compare_*.sh) reads the run's outputs in place.
#
# Usage: ./save_reference.sh <case_name> [--from-variant <tag>]
#
# Copies, from where the run wrote them (see lib/run_paths.sh):
#   NODE.001_01                       -> references/<case_name>/NODE.001_01
#   <tag> netCDF  (per netcdf_vars)   -> references/<case_name>/netcdf/<tag>.nc
#   <fname> FA/GRIB (per fa_grib_files) -> references/<case_name>/fa_grib/<fname>
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

source "$here/lib/run_paths.sh"
src_node="$(rp_node "$run_id")"

[ -f "$src_node" ] || { echo "No $src_node to promote (run this case first / right host?)." >&2; exit 1; }

ref_dir="$here/references/$case_name"
mkdir -p "$ref_dir"
cp "$src_node" "$ref_dir/NODE.001_01"
echo ">>> Saved reference: $ref_dir/NODE.001_01  (from $src_node)"

netcdf_vars_file="$here/cases/$case_name/netcdf_vars"
if [ -f "$netcdf_vars_file" ]; then
    mkdir -p "$ref_dir/netcdf"
    while IFS= read -r tag; do
        tag="$(echo -n "${tag%%#*}" | xargs)"
        [ -z "$tag" ] && continue
        src="$(rp_netcdf "$run_id" "$tag")"
        if [ -f "$src" ]; then
            cp "$src" "$ref_dir/netcdf/$tag.nc"
            echo ">>> Saved reference: $ref_dir/netcdf/$tag.nc  (from $src)"
        else
            echo "Warning: no run output for '$tag' ($src) -- skipped." >&2
        fi
    done < "$netcdf_vars_file"
fi

fa_grib_files_file="$here/cases/$case_name/fa_grib_files"
if [ -f "$fa_grib_files_file" ]; then
    mkdir -p "$ref_dir/fa_grib"
    while IFS= read -r fname; do
        fname="$(echo -n "${fname%%#*}" | xargs)"
        [ -z "$fname" ] && continue
        src="$(rp_fa_grib "$run_id" "$fname")"
        if [ -f "$src" ]; then
            cp "$src" "$ref_dir/fa_grib/$fname"
            echo ">>> Saved reference: $ref_dir/fa_grib/$fname  (from $src)"
        else
            echo "Warning: no run output for '$fname' ($src) -- skipped." >&2
        fi
    done < "$fa_grib_files_file"
fi
