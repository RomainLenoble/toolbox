#!/usr/bin/env python3
import os
import shutil
import subprocess
import tempfile

import yaml


def load_config(config_path):
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def _fmt(values, decimals):
    return ", ".join(f"{v:.{decimals}f}" for v in values)


def _fortran_bool(value):
    return ".TRUE." if value else ".FALSE."


def interpole_file(fic_aer, fic_out, config):
    """Interpolate a single ERA5 file to the target domain with GL.

    `config` is a dict loaded from one of the YAML files in config/
    (see load_config / --config on the calling scripts).

    Each call gets its own scratch working directory so concurrent calls
    (multiprocessing workers, MPI ranks, or independent job submissions)
    never share the "climate_aladin" symlink or "naminterp" file in a
    common cwd. Without this, parallel workers race on
    `if not os.path.exists("climate_aladin"): os.symlink(...)` and can
    raise FileExistsError, or worse, one worker's gl subprocess can read
    a naminterp file half-written by another worker.
    """

    site = config["site"]
    domain = config["domain"]
    levels = config["vertical_levels"]
    nml = config.get("namelist", {})

    gl_bin = os.path.join(site["gl_bin_dir"], "gl")
    geom = domain["name"]
    climate_file = domain["climate_file"].format(name=geom)

    ahalf = _fmt(levels["ahalf"], 6)
    bhalf = _fmt(levels["bhalf"], 12)

    namelist_content = f"""&NAMINTERP
  OUTGEO%NLEV={levels['nlev']},
  AHALF={ahalf}
  BHALF={bhalf}
  ORDER={levels['order']},
  NE2EALG={levels['ne2ealg']},
  printlev = {nml.get('printlev', 0)},
  lnhdyn={_fortran_bool(nml.get('lnhdyn', True))},
  lqgp={_fortran_bool(nml.get('lqgp', True))},
  LATMKEY_ONLY={_fortran_bool(nml.get('latmkey_only', False))},
  lskip_surface={_fortran_bool(nml.get('lskip_surface', True))},
/
"""

    fic_aer_abs = os.path.abspath(fic_aer)
    fic_out_abs = os.path.abspath(fic_out)

    scratch_dir = site.get("scratch_dir") or None
    workdir = tempfile.mkdtemp(prefix="gl_interp_", dir=scratch_dir)
    try:
        os.symlink(climate_file, os.path.join(workdir, "climate_aladin"))
        with open(os.path.join(workdir, "naminterp"), "w") as f:
            f.write(namelist_content)

        cmd = [gl_bin, "-lbc", "ifs", "-n", "naminterp", fic_aer_abs, "-o", fic_out_abs]
        print("Running:", " ".join(cmd))
        subprocess.run(cmd, cwd=workdir, check=True)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
