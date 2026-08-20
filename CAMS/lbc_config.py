#!/home/gmgec/mrgo/lenobler/miniforge3/bin/python3
"""
Configuration loader for the CAMS -> LBC creation pipeline (create_LBC.py and
the scripts it drives).

All domain/path/naming/runtime parameters that used to be hardcoded in the
various scripts now live in a YAML config file (see CAMS/config/ALPX3.yaml
for a fully documented example/template). Copy that file and adjust it when
switching to a new domain, HPC install, or file naming convention.

Usage:
    from lbc_config import load_config
    config = load_config("/path/to/config.yaml")
"""
import copy
import os
import re

import yaml

# Default values. Anything left unset in the user's YAML file falls back to
# these. Required values (paths.gl_bin, paths.climate_file, domain.name,
# domain.nlev, domain.ahalf, domain.bhalf) intentionally have no default and
# must be provided in the YAML file.
DEFAULTS = {
    "paths": {
        "gl_bin": None,
        "climate_file": None,
        "env_setup": "",
        # Directory containing the pipeline scripts (interpole_current_folder.py,
        # Interpol_CAMS_to_ALPX3.py, interpolate_grib_hourly_epygram.py,
        # merge_LBC.py, merge_files.py). Defaults to the directory containing
        # this file (i.e. this repo's CAMS/ folder), so the pipeline works
        # regardless of where it is checked out.
        "scripts_dir": None,
    },
    "domain": {
        "name": None,
        "nlev": None,
        "ahalf": None,
        "bhalf": None,
    },
    "aerosols": {
        "cams_shortnames": [f"aermr{i:02d}" for i in range(1, 12)],
        "mmr_faname": [
            "SEASALT1_MMR", "SEASALT2_MMR", "SEASALT3_MMR",
            "DUST1_MMR", "DUST2_MMR", "DUST3_MMR",
            "OM1_MMR", "OM2_MMR",
            "BC1_MMR", "BC2_MMR",
            "SULF_MMR",
        ],
    },
    "naming": {
        # Prefix (after {geom} substitution) used to select raw CAMS files
        # to interpolate, e.g. "CAMS_ALPX3_2012" -> "CAMS_{geom}_2012".
        "cams_input_prefix": "CAMS_{geom}_",
        # Regex used to extract the datetime string from raw CAMS filenames.
        "cams_input_datetime_regex": r"(\d{4}-\d{2}-\d{2}-\d{2})",
        "cams_input_datetime_format": "%Y-%m-%d-%H",
        # Prefix used for CAMS files once interpolated onto the target grid.
        "cams_interp_prefix": "CAMS_AROME_",
        # Prefix of the ERA5 LBC files to merge with the interpolated CAMS files.
        "era5_prefix": "{geom}_ERA5_CAMS_",
        # Prefix used for the final merged output files.
        "merge_output_prefix": "{geom}_ERA5_CAMS_",
    },
    "runtime": {
        "nproc_time_interp": 10,
        "max_workers_merge": 16,
        "match_tolerance_hours": 1,
    },
}

_REQUIRED_KEYS = [
    ("paths", "gl_bin"),
    ("paths", "climate_file"),
    ("domain", "name"),
    ("domain", "nlev"),
    ("domain", "ahalf"),
    ("domain", "bhalf"),
]

# Naming keys that support a "{geom}" placeholder, substituted with domain.name.
_GEOM_TEMPLATED_KEYS = [
    ("paths", "climate_file"),
    ("naming", "cams_input_prefix"),
    ("naming", "era5_prefix"),
    ("naming", "merge_output_prefix"),
]


def _deep_merge(base, override):
    """Recursively merge `override` into a copy of `base` (override wins)."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _validate(config, config_path):
    missing = [
        f"{section}.{key}"
        for section, key in _REQUIRED_KEYS
        if config.get(section, {}).get(key) is None
    ]
    if missing:
        raise ValueError(
            f"Config file '{config_path}' is missing required key(s): "
            f"{', '.join(missing)}"
        )

    nlev = config["domain"]["nlev"]
    for key in ("ahalf", "bhalf"):
        values = config["domain"][key]
        if len(values) != nlev + 1:
            raise ValueError(
                f"Config file '{config_path}': domain.{key} must have "
                f"nlev+1={nlev + 1} values, got {len(values)}"
            )


def _resolve(config):
    geom = config["domain"]["name"]

    for section, key in _GEOM_TEMPLATED_KEYS:
        value = config[section][key]
        if isinstance(value, str):
            config[section][key] = value.format(geom=geom)

    if config["paths"]["scripts_dir"] is None:
        config["paths"]["scripts_dir"] = os.path.dirname(os.path.abspath(__file__))
    else:
        config["paths"]["scripts_dir"] = os.path.abspath(
            os.path.expanduser(config["paths"]["scripts_dir"])
        )

    return config


def load_config(config_path):
    """Load, validate, and resolve a YAML LBC pipeline config file."""
    with open(config_path) as f:
        user_config = yaml.safe_load(f) or {}

    config = _deep_merge(DEFAULTS, user_config)
    _validate(config, config_path)
    config = _resolve(config)
    return config


def namelist_float_list(values, decimals=6):
    """Format a list of floats as a comma-separated string for a Fortran namelist."""
    return ", ".join(f"{v:.{decimals}f}" for v in values)
