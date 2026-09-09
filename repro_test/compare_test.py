#!/usr/bin/env python3
"""Compare one case's (or one variant's) run outputs against the case's
stored references -- or, with --against, against another run of the same
case (a bit-reproducibility check).

Covers the NODE.001_01 log always, plus -- when the case has a
cases/<name>/netcdf_vars and/or cases/<name>/fa_grib_files list -- its
netCDF and FA/GRIB outputs (delegating to compare_netcdf.py /
compare_fa_grib.py).

The run's outputs are read *in place* from where the job wrote them (see
lib/paths.py) -- nothing is copied. Only the diff reports land under
results/<run_id>/. Run this on a host that can see the run tree (or set
$REPRO_RUN_BASE to a mount of it).

Usage: compare_test.py <case_name> [--variant <tag>] [--against <tag>] [run_NODE_path] [-- diff_NODE options]

    --variant <tag>   which run's outputs to check (run_id "<case>__<tag>";
                       omitted = "<case>").
    --against <tag2>  compare against run "<case>__<tag2>" instead of the
                       stored reference, and demand *bit-exact* agreement
                       (diff_NODE --rtol 0 --atol 0 --atol-frac 0 --gpnorms '*',
                       diff_netcdf/diff_fa_grib --rel-max-diff 0). Use to
                       check a new executable reproduces itself run-to-run.
                       cases/<name>/node_diff_args is skipped in this mode.
    run_NODE_path     override the run's NODE.001_01 path (default: live).
    after "--"        extra options for diff_NODE only.

Exit: 0 if everything agrees, 1 if any comparison FAILs, 2 if none FAILed
but some comparison could not run.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import compare_fa_grib
import compare_netcdf
from lib.common import HERE, read_diff_args, run_diff, split_ddash, timestamp
from lib.paths import RunPaths


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    left, diff_node_opts = split_ddash(argv)

    p = argparse.ArgumentParser(prog="compare_test.py", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("case_name")
    p.add_argument("--variant", default="")
    p.add_argument("--against", default="")
    p.add_argument("run_node_path", nargs="?", default="")
    args = p.parse_args(left)

    case_name = args.case_name
    run_id = f"{case_name}__{args.variant}" if args.variant else case_name
    label = f"{case_name} (variant: {args.variant})" if args.variant else case_name

    against_run_id = ""
    if args.against:
        against_run_id = f"{case_name}__{args.against}"
        label = f"{label}  [repro: vs {args.against}]"

    rp = RunPaths(HERE, case_name)

    result = Path(args.run_node_path) if args.run_node_path else rp.node(run_id)

    if against_run_id:
        ref = rp.node(against_run_id)
        if not ref.is_file():
            print(f"Missing run NODE.001_01 for --against: {ref}", file=sys.stderr)
            return 1
    else:
        ref = HERE / "references" / case_name / "NODE.001_01"
        if not ref.is_file():
            print(f"Missing reference log: {ref}", file=sys.stderr)
            return 1
    if not result.is_file():
        print(f"Missing run NODE.001_01: {result}", file=sys.stderr)
        print("(is the job finished? are you on the right host? or pass its path as an argument)",
              file=sys.stderr)
        return 1

    # diff_NODE args:
    #   reference mode -> per-case cases/<case>/node_diff_args (tuned tolerances)
    #   --against mode -> bit-exact, compare everything; node_diff_args skipped
    if args.against:
        node_args = ["--rtol", "0", "--atol", "0", "--atol-frac", "0", "--gpnorms", "*"]
    else:
        node_args = read_diff_args(HERE / "cases" / case_name / "node_diff_args")

    report = HERE / "results" / run_id / f"diff_{timestamp()}.txt"

    any_fail = any_error = False

    # --- NODE.001_01 -----------------------------------------------------
    rc = run_diff("diff_NODE", [str(ref), str(result), *node_args, *diff_node_opts], report)
    if rc == 0:
        print(f"PASS  [{label} / NODE]")
    elif rc == 1:
        print(f"FAIL  [{label} / NODE]  -- see {report}")
        any_fail = True
    else:
        print(f"???   [{label} / NODE]  -- diff_NODE could not compare (rc={rc}, see {report})")
        any_error = True

    # forwarded to the netCDF / FA-GRIB sub-comparisons
    sub_args: list[str] = []
    if args.variant:
        sub_args += ["--variant", args.variant]
    if args.against:
        sub_args += ["--against", args.against]

    def tally(rc: int) -> None:
        nonlocal any_fail, any_error
        if rc == 1:
            any_fail = True
        elif rc != 0:
            any_error = True

    if (HERE / "cases" / case_name / "netcdf_vars").is_file():
        print()
        tally(compare_netcdf.main([case_name, *sub_args]))

    if (HERE / "cases" / case_name / "fa_grib_files").is_file():
        print()
        tally(compare_fa_grib.main([case_name, *sub_args]))

    print()
    if any_fail:
        print(f"FAIL  [{label}]  -- one or more comparisons out of tolerance")
        return 1
    if any_error:
        print(f"???   [{label}]  -- one or more comparisons could not run")
        return 2
    print(f"PASS  [{label}]  -- all comparisons agree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
