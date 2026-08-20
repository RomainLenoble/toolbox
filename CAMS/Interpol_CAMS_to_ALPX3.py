#!/usr/bin/env python3
import os
import sys
import subprocess
import textwrap
import numpy as np

from lbc_config import namelist_float_list

# CAMS aerosol shortnames (see config/*.yaml -> aerosols.cams_shortnames):
# 'aermr01', 'Sea Salt Aerosol (0.03 - 0.5 um) Mixing Ratio',
# 'aermr02', 'Sea Salt Aerosol (0.5 - 5 um) Mixing Ratio',
# 'aermr03', 'Sea Salt Aerosol (5 - 20 um) Mixing Ratio',
# 'aermr04',: 'Dust Aerosol (0.03 - 0.55 um) Mixing Ratio',
# 'aermr05', 'Dust Aerosol (0.55 - 0.9 um) Mixing Ratio',
# 'aermr06', 'Dust Aerosol (0.9 - 20 um) Mixing Ratio',
# 'aermr07', 'Hydrophilic Organic Matter Aerosol Mixing Ratio',
# 'aermr08', 'Hydrophobic Organic Matter Aerosol Mixing Ratio',
# 'aermr09', 'Hydrophilic Black Carbon Aerosol Mixing Ratio',
# 'aermr10', 'Hydrophobic Black Carbon Aerosol Mixing Ratio',
# 'aermr11', 'Sulphate Aerosol Mixing Ratio',


def interpole_file(fic_aer, fic_out, all_particles, list_FA_name=None, config=None, work_dir="."):
    """
    Interpolate one CAMS aerosol file onto the target domain grid using the
    external "gl" tool.

    config: dict returned by lbc_config.load_config(), holding the
        domain/paths/aerosols parameters (GL binary, climate file, vertical
        grid, CAMS shortnames, ...).
    work_dir: directory in which the transient "naminterp" namelist and
        "climate_aladin" symlink are created (defaults to the current
        working directory for backward compatibility).
    """
    if config is None:
        raise ValueError("interpole_file() requires a config dict (see lbc_config.load_config)")
    if list_FA_name is None:
        list_FA_name = []

    # Environment setup
    os.environ["ULIMIT"] = "unlimited"  # mimic ulimit -s unlimited

    gl_bin = config["paths"]["gl_bin"]
    climate_file = config["paths"]["climate_file"]

    nlev = config["domain"]["nlev"]
    ahalf = namelist_float_list(config["domain"]["ahalf"], decimals=6)
    bhalf = namelist_float_list(config["domain"]["bhalf"], decimals=10)
    cams_shortnames = config["aerosols"]["cams_shortnames"]

    climate_link = os.path.join(work_dir, "climate_aladin")
    naminterp_path = os.path.join(work_dir, "naminterp")

    # Climate file symlink
    if os.path.islink(climate_link) or os.path.exists(climate_link):
        os.remove(climate_link)
    os.symlink(climate_file, climate_link)

    # Write LIMA part of the namelist
    limap_lines = []
    if len(all_particles) > 0:
        limap_lines.append('  lmap2lima=T')
        for i, entry in enumerate(all_particles, start=1):
            use_short = ",".join(f"'{s}'" for s in entry["shortname"])
            block = textwrap.indent(textwrap.dedent(f"""\
                limap({i})%faname='{entry["faname"]}',      ! Faname in the ouput file
                limap({i})%use_shortname={use_short},       ! Cams name
                limap({i})%rho={entry["rho"]}.0,            ! density (kg/m**3)
                limap({i})%md={entry["r"]*1e6*2},           ! convert radius in m to diameter in microm
                limap({i})%sigma={entry["sigma"]},          ! sigma for log normal
            """), "  ")
            limap_lines.append(block)

    if len(all_particles) > 0:
        limap_content = "".join(limap_lines)
    elif list_FA_name:
        faname_list = ", ".join(f"'{name}'" for name in list_FA_name)
        limap_content = f"  atmkey(1:)%faname = {faname_list},"
    else:
        limap_content = ""

    shortname_list = ",".join(f"'{s}'" for s in cams_shortnames)
    intpm_list = ",".join("1" for _ in cams_shortnames)

    # Final namelist content with correct indentation
    namelist_content = f"""&NAMINTERP
  OUTGEO%NLEV={nlev},
  AHALF={ahalf}
  BHALF={bhalf}
  atmkey(1:)%shortname = {shortname_list},
  atmkey(1:)%intpm     = {intpm_list},
  ORDER=1
  NE2EALG=2,
  LATMKEY_ONLY=T,
  printlev = 0,
{limap_content}
/
"""
    # Write nml in file
    with open(naminterp_path, "w") as f:
        f.write(namelist_content)

    # Run gl
    cmd = [gl_bin, "-lbc", "ifs", "-n", naminterp_path, fic_aer, "-o", fic_out]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)