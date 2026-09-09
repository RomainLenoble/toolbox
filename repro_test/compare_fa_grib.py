#!/usr/bin/env python3
"""Compare a case's (or variant's) configured FA / GRIB outputs against
their stored references, field-by-field, via bin/diff_fa_grib (epygram) --
or, with --against, against another run.

Usage: compare_fa_grib.py <case_name> [--variant <tag>] [--against <tag>] [-- diff_fa_grib options]

Files to compare come from cases/<case_name>/fa_grib_files (one output
filename per line, "#" comments allowed), e.g.
    ICMSHNFR2+0001
    PFNFR2000+0003.grib
Each file is read in place from the run's rundir (same dir as NODE.001_01,
see lib/paths.py).

    default          -> diff against references/<case_name>/fa_grib/<filename>
    --against <tag2> -> diff against run "<case_name>__<tag2>" (bit-exact:
                         --rel-max-diff 0), for a reproducibility check

Unlike netcdf_vars (one field per file), each entry here is a whole FA/GRIB
file and diff_fa_grib iterates over every field inside it.

Exit: 1 if any field is out of tolerance, 2 if nothing could be compared,
0 otherwise.
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

    p = argparse.ArgumentParser(prog="compare_fa_grib.py", description=__doc__,
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

    files_list = HERE / "cases" / case_name / "fa_grib_files"
    if not files_list.is_file():
        print(f"No fa_grib_files list for case '{case_name}' (expected {files_list}) "
              f"-- nothing to compare.", file=sys.stderr)
        return 2

    rp = RunPaths(HERE, case_name)
    fnames = read_list(files_list)

    diff_defaults = ["--rel-max-diff", "0"] if args.against else []
    out_dir = HERE / "results" / run_id / "fa_grib"

    failed = missing = 0
    for fname in fnames:
        if against_run_id:
            ref, ref_what = rp.fa_grib(against_run_id, fname), f"run {against_run_id}"
        else:
            ref, ref_what = HERE / "references" / case_name / "fa_grib" / fname, "reference"
        exp = rp.fa_grib(run_id, fname)

        if not ref.is_file():
            print(f"???  [{label} / {fname}]  -- no {ref_what} at {ref}")
            missing = 1
            continue
        if not exp.is_file():
            print(f"???  [{label} / {fname}]  -- no run output at {exp} (job finished? right host?)")
            missing = 1
            continue

        report = out_dir / f"diff_{fname}_{timestamp()}.txt"
        rc = run_diff("diff_fa_grib", [str(ref), str(exp), *diff_defaults, *diff_opts], report)
        if rc == 0:
            print(f"PASS  [{label} / {fname}]")
        else:
            print(f"FAIL  [{label} / {fname}]  -- see {report}")
            failed = 1
        print()

    if not fnames:
        print(f"Nothing was compared -- is {files_list} empty?")
    if failed:
        return 1
    if missing or not fnames:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
