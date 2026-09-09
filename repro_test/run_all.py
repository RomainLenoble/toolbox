#!/usr/bin/env python3
"""Launch every case under cases/, optionally with the same override applied
to all of them (e.g. testing a new executable across every case).

Usage: run_all.py [--variant <tag>] [--set KEY=VALUE ...] [--repro] [-- extra param_Eclis args]

See run_test.py for what --variant/--set/--repro do. A non-zero result from
one case (FAIL / couldn't compare) doesn't stop the rest; the count is
reported at the end.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_test
from lib.common import HERE


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0

    failed = 0
    for case_dir in sorted(d for d in (HERE / "cases").iterdir() if d.is_dir()):
        if run_test.main([case_dir.name, *argv]) != 0:
            failed += 1
        print()

    print(f"=== run_all: {failed} case(s) reported a non-zero result ===")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
