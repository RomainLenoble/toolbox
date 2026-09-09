"""Small shared helpers for the repro_test wrapper scripts."""

from __future__ import annotations

import datetime as _dt
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


def timestamp() -> str:
    return _dt.datetime.now().strftime("%Y%m%dT%H%M%S")


def split_ddash(argv: list[str]) -> tuple[list[str], list[str]]:
    """Split ``[...] -- [passthrough...]`` on the first bare ``--``."""
    if "--" in argv:
        i = argv.index("--")
        return argv[:i], argv[i + 1 :]
    return argv, []


def _strip_comment(line: str) -> str:
    return line.split("#", 1)[0].strip()


def read_list(path: Path) -> list[str]:
    """One entry per line, ``#`` comments and blank lines dropped."""
    if not path.is_file():
        return []
    return [c for c in (_strip_comment(l) for l in path.read_text().splitlines()) if c]


def read_diff_args(path: Path) -> list[str]:
    """Whitespace-separated tokens from a per-case args file, ``#`` comments,
    quotes respected (old: ``sed 's/#.*//' | xargs -n1``)."""
    if not path.is_file():
        return []
    text = "\n".join(l.split("#", 1)[0] for l in path.read_text().splitlines())
    return shlex.split(text)


# ---------------------------------------------------------------------------
# labels & report locations
# ---------------------------------------------------------------------------

def make_label(case_name: str, variant: str, against: str) -> str:
    """Short human label for terminal lines, e.g.
    ``NFR25/v7.4.dev vs v7.4.dev__rep`` or just ``NFR25``."""
    lab = f"{case_name}/{variant}" if variant else case_name
    return f"{lab} vs {against}" if against else lab


def safe_name(s: str) -> str:
    """Filesystem-safe version of an entry/filename for a report file."""
    return re.sub(r"[^A-Za-z0-9._+-]", "_", s).strip("_") or "x"


def report_dir(run_id: str, against: str) -> Path:
    """The directory a compare_* run writes its detail files into:

        results/<run_id>/vs-reference_<ts>/        (normal)
        results/<run_id>/vs-<against>_<ts>/        (--against / --repro)
    """
    mode = f"vs-{safe_name(against)}" if against else "vs-reference"
    d = HERE / "results" / run_id / f"{mode}_{timestamp()}"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------------------
# running the bin/diff_* tools
# ---------------------------------------------------------------------------

# lines worth echoing to the terminal from an otherwise file-only diff report
_SALIENT = re.compile(
    r"WARNING|MISMATCH|ERROR|<-- FAIL|\bonly in (ref|exp)\b|^\s*(PASS|FAIL):|\*\s*$"
)


def run_diff(tool: str, args: list[str], report: Path, *, verbose: bool = False) -> int:
    """Run bin/<tool>, capture ALL its output to ``report``. Returns the exit
    code. Terminal output: everything if ``verbose``; otherwise nothing on a
    clean pass, and only the salient lines (warnings / flagged rows / verdict)
    when the tool reports a problem."""
    cmd = [sys.executable, str(HERE / "bin" / tool), *args]
    env = {**os.environ, "PYTHONUNBUFFERED": "1"}
    proc = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env
    )
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(proc.stdout)

    if verbose:
        sys.stdout.write(proc.stdout)
    elif proc.returncode != 0:
        for line in proc.stdout.splitlines():
            if _SALIENT.search(line):
                print(f"      | {line.rstrip()}")

    return proc.returncode
