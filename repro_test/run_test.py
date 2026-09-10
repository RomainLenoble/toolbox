#!/usr/bin/env python3
"""Launch one repro_test case, optionally overriding a param_Eclis variable
(e.g. to test a new executable while keeping everything else fixed), wait
for the resulting NODE.001_01 to be written and stop changing, then compare
the run's outputs (in place, not copied) against the case's references via
compare_test.py.

Usage:
  run_test.py <case_name> [--variant <tag>] [--set KEY=VALUE ...] \\
      [--repro] [--repro-set KEY=VALUE ...] [--no-compare] \\
      [--no-wait] [--poll-interval SEC] [--timeout SEC] [-- extra param_Eclis args]

  --variant <tag>      Run under EXPID "<case_name>__<tag>" instead of
                        "<case_name>". Required with --repro.
  --set KEY=VALUE      Patch the `KEY=...` assignment line in param_Eclis
                        (e.g. --set pack=/home/.../arome_v7.5.../). Repeatable.
  --repro             Also launch a SECOND, identical run under
                        "<case>__<tag>__rep" and, once both finish, do:
                          [1/2] <tag> vs <tag>__rep -- bit-reproducible? (bit-exact)
                          [2/2] <tag> vs saved reference -- still matches? (case tolerances)
  --repro-set KEY=VALUE  Extra override applied to the __rep run only (e.g.
                        --repro-set NODE_ARP=3 -- a stronger repro test). Repeatable.
  --no-compare        Submit + wait, but don't run the comparison(s).
  --no-wait           Just submit and return: print the command(s) to run later.
  --poll-interval SEC  How often to check NODE.001_01 (default 20).
  --timeout SEC       Give up waiting after this long (default 7200 = 2h).

Copies cases/<case_name>/launch/ into .runs/<run_id>/ (run_id's basename
becomes EXPID) and launches param_Eclis from there. param_Eclis's own
(very verbose) output goes to results/<run_id>/launch.log.

Exit (with --repro): 0 if both checks pass, 1 if either FAILs, 2 if either
could not run. Otherwise relays compare_test.py's exit code.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import compare_test
from lib.common import HERE, split_ddash
from lib.paths import RunPaths


def apply_override(param_file: Path, key: str, value: str) -> None:
    pat = re.compile(r"^" + re.escape(key) + r"=.*")
    lines = param_file.read_text().splitlines()
    if not any(pat.match(l) for l in lines):
        print(f"Warning: no '{key}=...' line found in param_Eclis to override", file=sys.stderr)
    new = [pat.sub(lambda _m: f"{key}={value}", l) if pat.match(l) else l for l in lines]
    param_file.write_text("\n".join(new) + "\n")


def prepare_and_submit(rp: RunPaths, launch_src: Path, run_id: str,
                       overrides: list[str], extra_launch_args: list[str]) -> None:
    """Prepare .runs/<run_id>/ from the case's launch/, apply overrides, submit."""
    rdir = HERE / ".runs" / run_id
    if rdir.exists():
        shutil.rmtree(rdir)
    rdir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(launch_src, rdir)

    param_file = rdir / "param_Eclis"
    for kv in overrides:
        key, _, value = kv.partition("=")
        apply_override(param_file, key, value)
        print(f">>> [{run_id}] override: {key}={value}")

    result_dir = HERE / "results" / run_id
    result_dir.mkdir(parents=True, exist_ok=True)
    log = result_dir / "launch.log"
    print(f">>> [{run_id}] launching from {rdir} (EXPID={run_id}); param_Eclis output -> {log}")

    import subprocess

    # param_Eclis is interactive (prompts for confirmation on stdin) and long
    # running; launch it detached, feeding a stream of "y" via `yes`, with its
    # combined output going to launch.log. We don't wait here -- wait_for_node()
    # polls NODE.001_01 as the synchronization point.
    yes = subprocess.Popen(["yes"], stdout=subprocess.PIPE)
    with open(log, "w") as fh:
        proc = subprocess.Popen(
            ["./param_Eclis"], cwd=rdir,
            stdin=yes.stdout, stdout=fh, stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    yes.stdout.close()  # let `yes` receive SIGPIPE once param_Eclis exits
    del extra_launch_args  # unused until extra launch args are wired up
    print(f">>> [{run_id}] submitted (pid {proc.pid}).")


def wait_for_node(rp: RunPaths, run_id: str, poll: float, timeout: float) -> None:
    """Block until <run_id>'s NODE.001_01 exists and has stopped growing."""
    node = rp.node(run_id)
    waited = 0.0
    print(f">>> [{run_id}] waiting for {node} (poll {poll:g}s, timeout {timeout:g}s)...")
    while not node.is_file():
        if waited >= timeout:
            sys.exit(f"!!! [{run_id}] timed out waiting for {node} to appear.")
        time.sleep(poll)
        waited += poll

    prev = None
    stable = 0
    while stable < 3:
        if waited >= timeout:
            sys.exit(f"!!! [{run_id}] timed out waiting for {node} to stabilize.")
        time.sleep(poll)
        waited += poll
        try:
            st = node.stat()
            cur = (st.st_mtime, st.st_size)
        except OSError:
            cur = None
        stable = stable + 1 if cur is not None and cur == prev else 0
        prev = cur
    print(f">>> [{run_id}] NODE.001_01 ready.")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    left, extra_launch_args = split_ddash(argv)

    p = argparse.ArgumentParser(prog="run_test.py", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("case_name")
    p.add_argument("--variant", default="")
    p.add_argument("--set", dest="overrides", action="append", default=[], metavar="KEY=VALUE")
    p.add_argument("--repro", action="store_true")
    p.add_argument("--repro-set", dest="repro_overrides", action="append", default=[],
                   metavar="KEY=VALUE")
    p.add_argument("--no-compare", action="store_true")
    p.add_argument("--no-wait", action="store_true")
    p.add_argument("-v", "--verbose", action="store_true",
                   help="stream the full diff tables (default: concise + detail files)")
    p.add_argument("--maps", action="store_true",
                   help="draw the FA/GRIB exp-ref difference maps (already the default)")
    p.add_argument("--no-maps", action="store_true",
                   help="skip the FA/GRIB exp-ref difference maps")
    p.add_argument("--poll-interval", type=float, default=20)
    p.add_argument("--timeout", type=float, default=7200)
    args = p.parse_args(left)

    case_name = args.case_name
    launch_src = HERE / "cases" / case_name / "launch"
    if not launch_src.is_dir():
        print(f"No such case: {case_name} (expected {launch_src})", file=sys.stderr)
        return 1

    if args.repro and not args.variant:
        print("--repro needs --variant <tag> (the two runs need distinct EXPIDs).", file=sys.stderr)
        return 1

    run_id = f"{case_name}__{args.variant}" if args.variant else case_name
    rep_run_id = f"{run_id}__rep"
    rp = RunPaths(HERE, case_name)

    # --- submit ------------------------------------------------------
    prepare_and_submit(rp, launch_src, run_id, args.overrides, extra_launch_args)
    if args.repro:
        prepare_and_submit(rp, launch_src, rep_run_id,
                           args.overrides + args.repro_overrides, extra_launch_args)

    if args.no_wait:
        v = f" --variant {args.variant}" if args.variant else ""
        print()
        print(">>> --no-wait given. Once the job(s) have finished, run:")
        if args.repro:
            print(f"    {HERE / 'compare_test.py'} {case_name}{v} --against {args.variant}__rep"
                  f"   # [1/2] bit-reproducibility")
            print(f"    {HERE / 'compare_test.py'} {case_name}{v}"
                  f"                              # [2/2] vs saved reference")
        else:
            print(f"    {HERE / 'compare_test.py'} {case_name}{v}")
        return 0

    # --- wait -------------------------------------------------------
    wait_for_node(rp, run_id, args.poll_interval, args.timeout)
    if args.repro:
        wait_for_node(rp, rep_run_id, args.poll_interval, args.timeout)

    if args.no_compare:
        print(">>> --no-compare given, done.")
        return 0

    # --- compare ----------------------------------------------------
    v_args = ["--variant", args.variant] if args.variant else []
    if args.verbose:
        v_args += ["--verbose"]
    if args.no_maps:
        v_args += ["--no-maps"]

    if args.repro:
        bar = "=" * 70
        print(f"\n{bar}\n  [1/2] bit-reproducibility of the executable:  "
              f"{args.variant}  vs  {args.variant}__rep\n{bar}")
        rc_repro = compare_test.main([case_name, *v_args, "--against", f"{args.variant}__rep"])

        print(f"\n{bar}\n  [2/2] vs saved reference:  {args.variant}  vs  "
              f"references/{case_name}/\n{bar}")
        rc_ref = compare_test.main([case_name, *v_args])

        verdict = {0: "PASS", 1: "FAIL  -- the two identical runs differ",
                   2: "???   -- could not compare"}
        verdict_ref = {0: "PASS", 1: "FAIL  -- differs from the known-good result",
                       2: "???   -- could not compare"}
        print(f"\n=== executable test summary [{case_name} / {args.variant}] ===")
        print(f"  bit-reproducible : {verdict.get(rc_repro, verdict[2])}")
        print(f"  vs reference     : {verdict_ref.get(rc_ref, verdict_ref[2])}")
        if rc_repro == 0 and rc_ref == 0:
            return 0
        if rc_repro == 1 or rc_ref == 1:
            return 1
        return 2

    print("\n>>> Run finished. Comparing its outputs (in place) against references...")
    return compare_test.main([case_name, *v_args])


if __name__ == "__main__":
    sys.exit(main())
