#!/usr/bin/env python3
"""Promote a run's live output into a case's stored reference
(references/<case_name>/...). Use this once, on a run you trust, to
establish or update what future runs of that case get checked against --
typically a baseline run (no --variant).

This is the one place a copy happens: the reference has to live in the
repo. Everything else (compare_*.py) reads the run's outputs in place.

Usage: save_reference.py <case_name> [--from-variant <tag>]

Copies, from where the run wrote them (see lib/paths.py):
    NODE.001_01                          -> references/<case_name>/NODE.001_01
    <tag> netCDF   (per netcdf_vars)     -> references/<case_name>/netcdf/<tag>.nc
    <fname> FA/GRIB (per fa_grib_files)  -> references/<case_name>/fa_grib/<fname>
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.common import HERE, read_list
from lib.paths import RunPaths


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="save_reference.py", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("case_name")
    p.add_argument("--from-variant", default="", dest="from_variant")
    args = p.parse_args(sys.argv[1:] if argv is None else argv)

    case_name = args.case_name
    run_id = f"{case_name}__{args.from_variant}" if args.from_variant else case_name

    rp = RunPaths(HERE, case_name)
    src_node = rp.node(run_id)
    if not src_node.is_file():
        print(f"No {src_node} to promote (run this case first / right host?).", file=sys.stderr)
        return 1

    ref_dir = HERE / "references" / case_name
    ref_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(src_node, ref_dir / "NODE.001_01")
    print(f">>> Saved reference: {ref_dir / 'NODE.001_01'}  (from {src_node})")

    for tag in read_list(HERE / "cases" / case_name / "netcdf_vars"):
        (ref_dir / "netcdf").mkdir(parents=True, exist_ok=True)
        src = rp.netcdf(run_id, tag)
        if src.is_file():
            shutil.copy(src, ref_dir / "netcdf" / f"{tag}.nc")
            print(f">>> Saved reference: {ref_dir / 'netcdf' / (tag + '.nc')}  (from {src})")
        else:
            print(f"Warning: no run output for '{tag}' ({src}) -- skipped.", file=sys.stderr)

    for fname in read_list(HERE / "cases" / case_name / "fa_grib_files"):
        (ref_dir / "fa_grib").mkdir(parents=True, exist_ok=True)
        src = rp.fa_grib(run_id, fname)
        if src.is_file():
            shutil.copy(src, ref_dir / "fa_grib" / fname)
            print(f">>> Saved reference: {ref_dir / 'fa_grib' / fname}  (from {src})")
        else:
            print(f"Warning: no run output for '{fname}' ({src}) -- skipped.", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
