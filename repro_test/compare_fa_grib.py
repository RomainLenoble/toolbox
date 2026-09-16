#!/usr/bin/env python3
"""Compare a case's (or variant's) configured FA / GRIB outputs against
their stored references, field-by-field, via bin/diff_fa_grib (epygram) --
or, with --against, against another run.

Usage: compare_fa_grib.py <case_name> [--variant <tag>] [--against <tag>] [-v] [-- diff_fa_grib options]

Files to compare come from cases/<case_name>/fa_grib_files (one output
filename per line, "#" comments ok). Each file is read in place from the
run's rundir (same dir as NODE.001_01, see lib/paths.py); diff_fa_grib
iterates over every field inside it.

    default          -> diff against references/<case_name>/fa_grib/<filename>
    --against <tag2> -> diff against run "<case_name>__<tag2>" (bit-exact:
                         --rel-max-diff 0), for a reproducibility check

Terminal output is one PASS/FAIL/??? line per file; the full per-field
table is written to results/<run_id>/vs-*/fa_grib/<filename>.txt. -v /
--verbose streams the tables too.

--maps writes, next to that report, a difference-map PNG for every field
that is out of tolerance (results/<run_id>/vs-*/fa_grib/<filename>.maps/).
Pass diff_fa_grib's own --plot-when / --plot-layout after "--" to tune it.

Exit: 1 if any file is out of tolerance, 2 if nothing could be compared,
0 otherwise.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.common import HERE, make_label, read_list, report_dir, run_diff, safe_name, split_ddash
from lib.paths import RunPaths


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    left, diff_opts = split_ddash(argv)

    p = argparse.ArgumentParser(prog="compare_fa_grib.py", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("case_name")
    p.add_argument("--variant", default="")
    p.add_argument("--against", default="")
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("--maps", action="store_true",
                   help="also write exp-ref difference-map PNGs for flagged fields")
    p.add_argument("--report-dir", default="", help=argparse.SUPPRESS)
    args = p.parse_args(left)

    plot_opts_given = any(o.startswith("--plot") for o in diff_opts)

    case_name = args.case_name
    run_id = f"{case_name}_{args.variant}" if args.variant else case_name
    label = make_label(case_name, args.variant, args.against)
    against_run_id = f"{case_name}_{args.against}" if args.against else ""

    files_list = HERE / "cases" / case_name / "fa_grib_files"
    if not files_list.is_file():
        print(f"No fa_grib_files list for case '{case_name}' (expected {files_list}) "
              f"-- nothing to compare.", file=sys.stderr)
        return 2

    rp = RunPaths(HERE, case_name)
    fnames = read_list(files_list)
    rdir = Path(args.report_dir) if args.report_dir else report_dir(run_id, args.against)
    diff_defaults = ["--rel-max-diff", "0"] if args.against else []  # bit-exact for repro

    failed = missing = 0
    for fname in fnames:
        if against_run_id:
            ref, ref_what = rp.fa_grib(against_run_id, fname), f"run {against_run_id}"
        else:
            ref = HERE / "references" / case_name / "fa_grib" / fname
            ref_what = "reference"
        exp = rp.fa_grib(run_id, fname)

        if not ref.is_file():
            print(f"???   [{label} / {fname}]  -- no {ref_what} at {ref}")
            missing = 1
            continue
        if not exp.is_file():
            print(f"???   [{label} / {fname}]  -- no run output at {exp}")
            missing = 1
            continue

        rep = rdir / "fa_grib" / f"{safe_name(fname)}.txt"
        map_args: list[str] = []
        maps_dir = rdir / "fa_grib" / f"{safe_name(fname)}.maps"
        if (args.maps or plot_opts_given) and "--plot-dir" not in diff_opts:
            map_args = ["--plot-dir", str(maps_dir)]
        rc = run_diff("diff_fa_grib",
                      [str(ref), str(exp), *diff_defaults, *map_args, *diff_opts],
                      rep, verbose=args.verbose)
        if rc == 0:
            print(f"PASS  [{label} / {fname}]")
        else:
            print(f"FAIL  [{label} / {fname}]  -- {rep}")
            failed = 1
        if maps_dir.is_dir() and any(maps_dir.iterdir()):
            print(f"      maps: {maps_dir}  ({sum(1 for _ in maps_dir.glob('*.png'))})")

    if not fnames:
        print(f"Nothing was compared -- is {files_list} empty?")
    if failed:
        return 1
    if missing or not fnames:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
