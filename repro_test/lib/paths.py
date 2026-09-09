"""Resolve where a run's *live* outputs sit -- Python port of the old
lib/run_paths.sh.

We compare those files in place against the stored references (or against
another run); nothing is copied except by save_reference.py.

Base dir is ``${REPRO_RUN_BASE:-$HOME/relances}/<GROUP>/<run_id>``. <GROUP>
and <INIDATE> are read from that run's param_Eclis (the ``.runs/<run_id>/``
copy if present, else ``cases/<case_name>/launch/``).
"""

from __future__ import annotations

import glob
import os
import re
from pathlib import Path


class RunPaths:
    def __init__(self, here: Path, case_name: str) -> None:
        self.here = Path(here)
        self.case_name = case_name

    # -- param_Eclis lookups ------------------------------------------------
    def _param_file(self, run_id: str) -> Path:
        pf = self.here / ".runs" / run_id / "param_Eclis"
        if not pf.is_file():
            pf = self.here / "cases" / self.case_name / "launch" / "param_Eclis"
        return pf

    def _param_var(self, run_id: str, name: str) -> str:
        """Value of the first ``^NAME=`` line, all whitespace stripped
        (matches the old `grep | cut -d= -f2 | tr -d '[:space:]'`)."""
        try:
            text = self._param_file(run_id).read_text()
        except OSError:
            return ""
        for line in text.splitlines():
            m = re.match(re.escape(name) + r"=(.*)$", line)
            if m:
                return re.sub(r"\s", "", m.group(1))
        return ""

    def _run_src(self, run_id: str) -> Path:
        group = self._param_var(run_id, "GROUP") or "TEST_SUITE"
        base = os.environ.get("REPRO_RUN_BASE") or str(Path.home() / "relances")
        return Path(base) / group / run_id

    # -- output locations ------------------------------------------------
    def node(self, run_id: str) -> Path:
        return self._run_src(run_id) / "rundir" / "NODE.001_01"

    def fa_grib(self, run_id: str, fname: str) -> Path:
        return self._run_src(run_id) / "rundir" / fname

    def netcdf(self, run_id: str, tag: str) -> Path:
        """Newest XIOS file matching the tag; if none exists yet, the glob
        pattern itself (so the caller can report a clean 'not found')."""
        ini = re.sub(r"\D", "", self._param_var(run_id, "INIDATE"))
        d = self._run_src(run_id) / "iox_keep" / ini
        matches = sorted(glob.glob(str(d / f"*_arpsfx_{tag}_*.nc")))
        return Path(matches[-1]) if matches else d / f"*_arpsfx_{tag}_*.nc"
