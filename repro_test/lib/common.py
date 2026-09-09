"""Small shared helpers for the repro_test wrapper scripts."""

from __future__ import annotations

import datetime as _dt
import os
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


def run_diff(tool: str, args: list[str], report: Path | None) -> int:
    """Run bin/<tool>, stream its output to the terminal and (if given) to
    ``report``. Returns the tool's exit code."""
    cmd = [sys.executable, str(HERE / "bin" / tool), *args]
    env = {**os.environ, "PYTHONUNBUFFERED": "1"}
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env
    )
    captured: list[str] = []
    assert proc.stdout is not None
    for line in proc.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
        captured.append(line)
    rc = proc.wait()
    if report is not None:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text("".join(captured))
    return rc
