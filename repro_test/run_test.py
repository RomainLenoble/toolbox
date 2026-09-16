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
                        "<case>__<tag>_rep" and, once both finish, do:
                          [1/2] <tag> vs <tag>_rep -- bit-reproducible? (bit-exact)
                          [2/2] <tag> vs saved reference -- still matches? (case tolerances)
  --repro-set KEY=VALUE  Extra override applied to the _rep run only (e.g.
                        --repro-set NODE_ARP=3 -- a stronger repro test). Repeatable.
  --no-compare        Submit + wait, but don't run the comparison(s).
  --no-wait           Just submit and return: print the command(s) to run later.
  --poll-interval SEC  How often to check NODE.001_01 (default 20).
  --timeout SEC       Give up waiting after this long (default 7200 = 2h).

Copies cases/<case_name>/launch/ into .runs/<run_id>/ (run_id's basename
becomes EXPID) and launches param_Eclis from there. param_Eclis's own
(very verbose) stdout/stderr go to .runs/<run_id>/out and .runs/<run_id>/err.

With --repro, after both runs finish, each is also checked for its
completion marker (last_NODE.001_01, the dir above rundir -- see
lib/paths.py): this confirms the run actually reached the end of the
forecast, rather than just "NODE.001_01 stopped changing for a while"
(which a crashed or stalled run can also produce). A missing marker never
turns a FAIL into anything else, but it does stop a comparison from being
reported as PASS -- printed instead as "??? -- could not compare".

Exit (with --repro): 0 if both checks pass, 1 if either FAILs, 2 if either
could not run (including: ran, but a run's completion marker is missing).
Otherwise relays compare_test.py's exit code.
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

    out_log = rdir / "out"
    err_log = rdir / "err"
    print(f">>> [{run_id}] launching from {rdir} (EXPID={run_id}); "
          f"param_Eclis output -> {out_log} / {err_log}")

    import subprocess

    # param_Eclis is interactive (prompts for confirmation on stdin) and long
    # running; launch it detached, feeding a stream of "y" via `yes`, with its
    # stdout/stderr going to separate files. We don't wait here --
    # wait_for_node() polls NODE.001_01 as the synchronization point.
    yes = subprocess.Popen(["yes"], stdout=subprocess.PIPE)
    with open(out_log, "w") as out_fh, open(err_log, "w") as err_fh:
        proc = subprocess.Popen(
            ["./param_Eclis"], cwd=rdir,
            stdin=yes.stdout, stdout=out_fh, stderr=err_fh,
            start_new_session=True,
        )
    yes.stdout.close()  # let `yes` receive SIGPIPE once param_Eclis exits
    del extra_launch_args  # unused until extra launch args are wired up
    print(f">>> [{run_id}] submitted (pid {proc.pid}).")


def wait_for_node(rp: RunPaths, run_id: str, poll: float, timeout: float) -> None:
    """Block until <run_id>'s NODE.001_01 is ready. Ready means either:

      * the completion marker `last_NODE.001_01` has appeared in the dir
        above rundir  (positive 'job finished' signal -- wins immediately), or
      * rundir/NODE.001_01 exists and its (mtime, size) has not changed for
        3 consecutive polls.

    The stop-changing check reads stat() over a shared filesystem, which can
    serve stale mtime/size while compute nodes are still writing -- so where
    the workflow leaves a marker, that is the signal that counts.
    """
    node = rp.node(run_id)
    done = rp.node_done_marker(run_id)
    waited = 0.0
    print(f">>> [{run_id}] waiting for {node}\n"
          f"        or marker {done}   (poll {poll:g}s, timeout {timeout:g}s)...")

    while not node.is_file():
        if done.is_file():
            print(f">>> [{run_id}] completion marker present -- run finished.")
            return
        if waited >= timeout:
            sys.exit(f"!!! [{run_id}] timed out waiting for {node} to appear.")
        time.sleep(poll)
        waited += poll

    prev = None
    stable = 0
    while stable < 3:
        if done.is_file():
            print(f">>> [{run_id}] completion marker present -- run finished.")
            return
        if waited >= timeout:
            sys.exit(f"!!! [{run_id}] timed out waiting for {node} to stabilize.")
        time.sleep(poll)
        waited += poll
        try:
            st = node.stat()
            cur = (st.st_mtime_ns, st.st_size)
        except OSError:
            cur = None
        stable = stable + 1 if cur is not None and cur == prev else 0
        prev = cur
    print(f">>> [{run_id}] NODE.001_01 unchanged for ~{3 * poll:g}s -- assuming ready.")


def confirm_reached_end(rp: RunPaths, run_id: str) -> bool:
    """True if <run_id> definitely reached the end of the forecast -- its
    completion marker last_NODE.001_01 (lib/paths.py) is present. This is
    distinct from wait_for_node()'s "NODE.001_01 stopped changing" fallback,
    which only *infers* completion and can be fooled by a stalled or
    crashed run that simply stopped writing."""
    marker = rp.node_done_marker(run_id)
    ok = marker.is_file()
    verdict = "reached the end" if ok else "did NOT reach the end -- no completion marker"
    print(f">>> [{run_id}] {verdict}: {marker}")
    return ok


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

    run_id = f"{case_name}_{args.variant}" if args.variant else case_name
    rep_run_id = f"{run_id}_rep"
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
            print(f"    {HERE / 'compare_test.py'} {case_name}{v} --against {args.variant}_rep"
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

    # --- did the run(s) actually reach the end? ------------------------
    reached_end = confirm_reached_end(rp, run_id)
    reached_end_rep = confirm_reached_end(rp, rep_run_id) if args.repro else True
    if args.repro and not (reached_end and reached_end_rep):
        print("!!! at least one run has no completion marker -- it may have crashed "
              "or stalled before finishing. The comparisons below may not be "
              "trustworthy.", file=sys.stderr)

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
              f"{args.variant}  vs  {args.variant}_rep\n{bar}")
        rc_repro = compare_test.main([case_name, *v_args, "--against", f"{args.variant}_rep"])

        print(f"\n{bar}\n  [2/2] vs saved reference:  {args.variant}  vs  "
              f"references/{case_name}/\n{bar}")
        rc_ref = compare_test.main([case_name, *v_args])

        if not (reached_end and reached_end_rep):
            # don't claim PASS on a comparison we can't vouch for -- a
            # matching / differing NODE from a run that never reached the
            # end is not the answer the check is supposed to give
            if rc_repro == 0:
                rc_repro = 2
            if rc_ref == 0:
                rc_ref = 2

        verdict = {0: "PASS", 1: "FAIL  -- the two identical runs differ",
                   2: "???   -- could not compare"}
        verdict_ref = {0: "PASS", 1: "FAIL  -- differs from the known-good result",
                       2: "???   -- could not compare"}
        print(f"\n=== executable test summary [{case_name} / {args.variant}] ===")
        print(f"  reached end      : {args.variant}={'yes' if reached_end else 'NO'}   "
              f"{args.variant}_rep={'yes' if reached_end_rep else 'NO'}")
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
