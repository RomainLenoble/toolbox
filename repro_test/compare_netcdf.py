#!/usr/bin/env python3
"""Compare a case's (or variant's) configured netCDF outputs against their
stored references -- or, with --against, against another run.

Usage: compare_netcdf.py <case_name> [--variant <tag>] [--against <tag>] [-- diff_netcdf options]

Which files to compare come from cases/<case_name>/netcdf_vars (one field
tag per line, e.g. "hour_zg", "#" comments allowed). The run's netCDF is
read in place from its XIOS iox_keep/ dir (see lib/paths.py).

    default          -> diff against references/<case_name>/netcdf/<tag>.nc
    --against <tag2> -> diff against run "<case_name>__<tag2>" (bit-exact:
                         --rel-max-diff 0), for a reproducibility check

Exit: 1 if any field is out of tolerance, 2 if nothing could be compared
(missing reference / missing run output / empty list), 0 otherwise.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.common import HERE, read_list, run_diff, split_ddash, timestamp
from lib.paths import RunPaths


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    left, diff_opts = split_ddash(argv)

    p = argparse.ArgumentParser(prog="compare_netcdf.py", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("case_name")
    p.add_argument("--variant", default="")
    p.add_argument("--against", default="")
    args = p.parse_args(left)

    case_name = args.case_name
    run_id = f"{case_name}__{args.variant}" if args.variant else case_name
    label = f"{case_name} (variant: {args.variant})" if args.variant else case_name

    against_run_id = ""
    if args.against:
        against_run_id = f"{case_name}__{args.against}"
        label = f"{label}  [repro: vs {args.against}]"

    vars_file = HERE / "cases" / case_name / "netcdf_vars"
    if not vars_file.is_file():
        print(f"No netcdf_vars file for case '{case_name}' (expected {vars_file}) "
              f"-- nothing to compare.", file=sys.stderr)
        return 2

    rp = RunPaths(HERE, case_name)
    tags = read_list(vars_file)

    # in --against (repro) mode, demand bit-exact agreement unless overridden
    diff_defaults = ["--rel-max-diff", "0"] if args.against else []
    out_dir = HERE / "results" / run_id / "netcdf"

    failed = missing = 0
    for tag in tags:
        if against_run_id:
            ref, ref_what = rp.netcdf(against_run_id, tag), f"run {against_run_id}"
        else:
            ref, ref_what = HERE / "references" / case_name / "netcdf" / f"{tag}.nc", "reference"
        exp = rp.netcdf(run_id, tag)

        if not ref.is_file():
            print(f"??? [{label} / {tag}]  -- no {ref_what} at {ref}")
            missing = 1
            continue
        if not exp.is_file():
            print(f"??? [{label} / {tag}]  -- no run output at {exp} (job finished? right host?)")
            missing = 1
            continue

        report = out_dir / f"diff_{tag}_{timestamp()}.txt"
        rc = run_diff("diff_netcdf", [str(ref), str(exp), *diff_defaults, *diff_opts], report)
        if rc == 0:
            print(f"PASS  [{label} / {tag}]")
        else:
            print(f"FAIL  [{label} / {tag}]  -- see {report}")
            failed = 1
        print()

    if not tags:
        print(f"Nothing was compared -- is {vars_file} empty?")
    if failed:
        return 1
    if missing or not tags:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
