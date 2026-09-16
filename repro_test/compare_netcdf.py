#!/usr/bin/env python3
"""Compare a case's (or variant's) configured netCDF outputs against their
stored references -- or, with --against, against another run.

Usage: compare_netcdf.py <case_name> [--variant <tag>] [--against <tag>] [-v] [-- diff_netcdf options]

Which files to compare come from cases/<case_name>/netcdf_vars (one entry
per line, "#" comments ok; see that file's header for the accepted forms).
The run's netCDF is read in place from its XIOS iox_keep/ dir (see lib/paths.py).

    default          -> diff against references/<case_name>/netcdf/<entry>
    --against <tag2> -> diff against run "<case_name>__<tag2>" (bit-exact:
                         --rel-max-diff 0), for a reproducibility check

Terminal output is one PASS/FAIL/??? line per entry; the full per-field
table is written to results/<run_id>/vs-*/netcdf/<entry>.txt. -v / --verbose
streams the tables too.

Exit: 1 if any entry is out of tolerance, 2 if nothing could be compared,
0 otherwise.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.common import HERE, make_label, read_list, report_dir, run_diff, safe_name, split_ddash
from lib.paths import RunPaths, netcdf_ref_name


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    left, diff_opts = split_ddash(argv)

    p = argparse.ArgumentParser(prog="compare_netcdf.py", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("case_name")
    p.add_argument("--variant", default="")
    p.add_argument("--against", default="")
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("--report-dir", default="", help=argparse.SUPPRESS)
    args = p.parse_args(left)

    case_name = args.case_name
    run_id = f"{case_name}_{args.variant}" if args.variant else case_name
    label = make_label(case_name, args.variant, args.against)
    against_run_id = f"{case_name}_{args.against}" if args.against else ""

    vars_file = HERE / "cases" / case_name / "netcdf_vars"
    if not vars_file.is_file():
        print(f"No netcdf_vars file for case '{case_name}' (expected {vars_file}) "
              f"-- nothing to compare.", file=sys.stderr)
        return 2

    rp = RunPaths(HERE, case_name)
    entries = read_list(vars_file)
    rdir = Path(args.report_dir) if args.report_dir else report_dir(run_id, args.against)
    diff_defaults = ["--rel-max-diff", "0"] if args.against else []  # bit-exact for repro

    failed = missing = 0
    for entry in entries:
        if against_run_id:
            ref, ref_what = rp.netcdf(against_run_id, entry), f"run {against_run_id}"
        else:
            ref = HERE / "references" / case_name / "netcdf" / netcdf_ref_name(entry)
            ref_what = "reference"
        exp = rp.netcdf(run_id, entry)

        if not ref.is_file():
            print(f"???   [{label} / {entry}]  -- no {ref_what} at {ref}")
            missing = 1
            continue
        if not exp.is_file():
            print(f"???   [{label} / {entry}]  -- no run output at {exp}")
            missing = 1
            continue

        rep = rdir / "netcdf" / f"{safe_name(entry)}.txt"
        rc = run_diff("diff_netcdf", [str(ref), str(exp), *diff_defaults, *diff_opts],
                      rep, verbose=args.verbose)
        if rc == 0:
            print(f"PASS  [{label} / {entry}]")
        else:
            print(f"FAIL  [{label} / {entry}]  -- {rep}")
            failed = 1

    if not entries:
        print(f"Nothing was compared -- is {vars_file} empty?")
    if failed:
        return 1
    if missing or not entries:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
