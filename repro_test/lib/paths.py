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


def netcdf_glob(entry: str) -> str:
    """The iox_keep/ filename pattern for one netcdf_vars entry.

    - explicit glob (contains * ? [)      -> used as-is
    - filename fragment (contains a '.')  -> "*<entry>"   e.g. _ps_202001-202002.nc
    - bare field tag                      -> "*_arpsfx_<tag>_*.nc"  e.g. hour_zg
    """
    if re.search(r"[*?\[]", entry):
        return entry
    if "." in entry:
        return f"*{entry}"
    return f"*_arpsfx_{entry}_*.nc"


def netcdf_ref_name(entry: str) -> str:
    """Stored-reference filename under references/<case>/netcdf/ for an entry."""
    name = entry.lstrip("*")
    return name if name.endswith(".nc") else f"{name}.nc"


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
        """The run's NODE.001_01. Normally rundir/NODE.001_01; once the run
        has finished and its rundir has been moved away, fall back to the
        `last_NODE.001_01` left in the directory above (see
        node_done_marker)."""
        primary = self._run_src(run_id) / "rundir" / "NODE.001_01"
        if not primary.is_file():
            marker = self.node_done_marker(run_id)
            if marker.is_file():
                return marker
        return primary

    def node_done_marker(self, run_id: str) -> Path:
        """`last_NODE.001_01` in the directory just above rundir -- written by
        the workflow only once the run is complete, so a positive
        'job finished' signal (unlike watching rundir/NODE.001_01 stop
        growing, which a shared filesystem can misreport)."""
        return self._run_src(run_id) / "last_NODE.001_01"

    def fa_grib(self, run_id: str, fname: str) -> Path:
        return self._run_src(run_id) / "rundir" / fname

    def netcdf(self, run_id: str, entry: str) -> Path:
        """Newest XIOS file matching a netcdf_vars entry; if none exists yet,
        the glob pattern itself (so the caller can report a clean 'not
        found'). See netcdf_glob() for how an entry is interpreted."""
        ini = re.sub(r"\D", "", self._param_var(run_id, "INIDATE"))
        d = self._run_src(run_id) / "iox_keep" / ini
        pat = netcdf_glob(entry)
        matches = sorted(glob.glob(str(d / pat)))
        return Path(matches[-1]) if matches else d / pat
