#!/usr/bin/env python3
"""Compare one case's (or one variant's) run outputs against the case's
stored references -- or, with --against, against another run of the same
case (a bit-reproducibility check).

Covers the NODE.001_01 log always, plus -- when the case has a
cases/<name>/netcdf_vars and/or cases/<name>/fa_grib_files list -- its
netCDF and FA/GRIB outputs (delegating to compare_netcdf.py /
compare_fa_grib.py).

Run outputs are read *in place* from where the job wrote them (see
lib/paths.py) -- nothing is copied. One directory of detail files is
written per invocation:

    results/<run_id>/vs-reference_<ts>/          (normal)
    results/<run_id>/vs-<against>_<ts>/          (--against / --repro)
        SUMMARY.txt        verdict + which detail file is which
        NODE.txt           full diff_NODE report
        netcdf/<entry>.txt
        fa_grib/<file>.txt
        fa_grib/<file>.maps/<field>.png   (exp-ref difference maps, on by default)

The terminal shows one PASS/FAIL/??? line per thing plus a short breakdown;
use -v / --verbose to also stream the full diff tables.

Usage: compare_test.py <case_name> [--variant <tag>] [--against <tag>] [-v] [--maps|--no-maps] [run_NODE_path] [-- diff_NODE options]

    --variant <tag>   which run's outputs to check (run_id "<case>__<tag>").
    --against <tag2>  compare against run "<case>__<tag2>" instead of the
                       stored reference, demanding *bit-exact* agreement
                       (diff_NODE --rtol 0 --atol 0 --atol-frac 0 --gpnorms '*',
                       diff_netcdf/diff_fa_grib --rel-max-diff 0).
                       cases/<name>/node_diff_args is skipped in this mode.
    --no-maps         skip the FA/GRIB difference-map PNGs (written by default
                       for every flagged field, capped at diff_fa_grib's
                       --plot-max).
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
from lib.common import HERE, make_label, read_diff_args, report_dir, run_diff, split_ddash
from lib.paths import RunPaths

_WORD = {0: "ok", 1: "FAIL (out of tolerance)", 2: "??? (could not compare)"}


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    left, diff_node_opts = split_ddash(argv)

    p = argparse.ArgumentParser(prog="compare_test.py", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("case_name")
    p.add_argument("--variant", default="")
    p.add_argument("--against", default="")
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("--maps", action="store_true",
                   help="draw the FA/GRIB exp-ref difference maps (already the default)")
    p.add_argument("--no-maps", action="store_true",
                   help="skip the FA/GRIB exp-ref difference maps")
    p.add_argument("run_node_path", nargs="?", default="")
    args = p.parse_args(left)
    maps = not args.no_maps   # on by default; --maps is accepted but redundant

    case_name = args.case_name
    run_id = f"{case_name}__{args.variant}" if args.variant else case_name
    label = make_label(case_name, args.variant, args.against)
    against_run_id = f"{case_name}__{args.against}" if args.against else ""

    rp = RunPaths(HERE, case_name)
    result = Path(args.run_node_path) if args.run_node_path else rp.node(run_id)

    if against_run_id:
        ref = rp.node(against_run_id)
        if not ref.is_file():
            print(f"???   [{label}]  -- no --against run NODE.001_01 at {ref}")
            return 2
    else:
        ref = HERE / "references" / case_name / "NODE.001_01"
        if not ref.is_file():
            print(f"???   [{label}]  -- no reference log at {ref}")
            return 2
    if not result.is_file():
        print(f"???   [{label}]  -- no run NODE.001_01 at {result}")
        print("      (is the job finished? are you on the right host? or pass its path as an arg)")
        return 2

    # diff_NODE args: reference mode -> per-case node_diff_args (tuned);
    #                 --against mode -> bit-exact, compare every field.
    if args.against:
        node_args = ["--rtol", "0", "--atol", "0", "--atol-frac", "0", "--gpnorms", "*"]
    else:
        node_args = read_diff_args(HERE / "cases" / case_name / "node_diff_args")

    rdir = report_dir(run_id, args.against)

    section: dict[str, int] = {}  # name -> 0 ok / 1 fail / 2 could-not-compare

    # --- NODE.001_01 ---------------------------------------------------
    node_argv = [*node_args, *diff_node_opts]
    if "--growth" in node_argv and "--plot" not in node_argv:
        node_argv += ["--plot", str(rdir / "NODE_growth.png")]
    rc = run_diff("diff_NODE", [str(ref), str(result), *node_argv],
                  rdir / "NODE.txt", verbose=args.verbose)
    section["NODE"] = rc if rc in (0, 1) else 2
    verdict = {0: "PASS", 1: "FAIL"}.get(rc, "??? ")
    tail = "" if rc == 0 else f"  -- {rdir / 'NODE.txt'}"
    print(f"{verdict}  [{label} / NODE]{tail}")
    if (rdir / "NODE_growth.png").exists():
        print(f"      plot: {rdir / 'NODE_growth.png'}")

    # --- netCDF / FA-GRIB (delegated) --------------------------------
    sub_args = ["--report-dir", str(rdir)]
    if args.variant:
        sub_args += ["--variant", args.variant]
    if args.against:
        sub_args += ["--against", args.against]
    if args.verbose:
        sub_args += ["--verbose"]

    if (HERE / "cases" / case_name / "netcdf_vars").is_file():
        rc = compare_netcdf.main([case_name, *sub_args])
        section["netCDF"] = rc if rc in (0, 1) else 2

    if (HERE / "cases" / case_name / "fa_grib_files").is_file():
        fa_args = [*sub_args, "--maps"] if maps else sub_args
        rc = compare_fa_grib.main([case_name, *fa_args])
        section["FA/GRIB"] = rc if rc in (0, 1) else 2

    # --- verdict + SUMMARY.txt ------------------------------------
    any_fail = 1 in section.values()
    any_error = 2 in section.values()
    overall = 1 if any_fail else (2 if any_error else 0)

    lines = [f"[{label}]", ""]
    lines += [f"    {n:8s}: {_WORD[r]}" for n, r in section.items()]
    lines.append("")
    lines.append({0: f"PASS  [{label}]  -- all comparisons agree",
                  1: f"FAIL  [{label}]  -- {', '.join(n for n, r in section.items() if r == 1)} out of tolerance",
                  2: f"???   [{label}]  -- {', '.join(n for n, r in section.items() if r == 2)} could not run"}[overall])
    (rdir / "SUMMARY.txt").write_text("\n".join(lines) + "\n")

    print()
    print("\n".join(lines))
    print(f"      detail: {rdir}")
    return overall


if __name__ == "__main__":
    sys.exit(main())
