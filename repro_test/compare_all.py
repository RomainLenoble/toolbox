#!/usr/bin/env python3
"""Compare every case (or every case's given variant) whose run has produced
a NODE.001_01, and print a summary. Does not stop at the first failure.

Usage: compare_all.py [--variant <tag>] [--against <tag>] [-- diff_NODE options]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import compare_test
from lib.common import HERE, split_ddash
from lib.paths import RunPaths


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    left, passthrough = split_ddash(argv)

    p = argparse.ArgumentParser(prog="compare_all.py", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--variant", default="")
    p.add_argument("--against", default="")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(left)

    common: list[str] = []
    if args.variant:
        common += ["--variant", args.variant]
    if args.against:
        common += ["--against", args.against]
    if args.verbose:
        common += ["--verbose"]

    failed = skipped = 0
    for case_dir in sorted(d for d in (HERE / "cases").iterdir() if d.is_dir()):
        case_name = case_dir.name
        run_id = f"{case_name}__{args.variant}" if args.variant else case_name
        node = RunPaths(HERE, case_name).node(run_id)
        if not node.is_file():
            print(f"SKIP  [{run_id}]  -- no NODE.001_01 at {node} yet")
            skipped += 1
            continue
        sub_argv = [case_name, *common]
        if passthrough:
            sub_argv += ["--", *passthrough]
        if compare_test.main(sub_argv) != 0:
            failed += 1
        print()

    print(f"=== summary: {failed} failed, {skipped} skipped ===")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
