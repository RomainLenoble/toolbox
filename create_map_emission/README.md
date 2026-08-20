# create_map_emission

Build an AROME/SURFEX "aerosol" FA file for a given date by extracting
CMIP7 emission fields (anthropogenic + open biomass burning: BC, OC, SO2)
from NetCDF datasets, regridding them onto the ALPX3 domain, and writing
them into a copy of a reference FA file (PGD or PREP).

## Files

| File | Purpose |
|---|---|
| `create_emission_date.py` | Main script: reads the reference FA geometry, extracts/regrids each configured emission variable for a target date, and writes the result to a new FA file. |
| `dict_var_to_treat.py` | Configuration: the list of emission variables to process (`variable_to_treat`), one dict per NetCDF variable. |

## How it works

1. Open the reference FA file (`prep_file_path`) with `epygram` and read a
   field from it just to obtain the target ALPX3 grid geometry.
2. Copy the reference file to `prep_file_out` — this is the file new fields
   get appended to. **This overwrites `prep_file_out` if it already exists.**
3. For each variable in `dict_var_to_treat.variable_to_treat`:
   - Open the source NetCDF file with `xarray` (to inspect the `time` /
     `sector` coordinates) and with `epygram` (to read and regrid the
     field).
   - Find the time step closest to the configured `date`.
   - If the variable has a `sector` dimension (e.g. energy, transport,
     residential, ...), sum all sectors to get the total emission.
   - Regrid the field onto the reference geometry
     (`extract_subdomain`).
   - Mask values outside `epygram.config.mask_outside` and multiply by the
     variable's `factor_conversion`.
   - Write the field to the output FA file under the id
     `FA_FIELD_PREFIX + varname_FA` (default prefix: `X001E_`).
4. Close the output file.

## Requirements

- Python 3 (developed against 3.12).
- [`epygram`](http://www.umr-cnrm.fr/gmapdoc/spip.php?article193) (Météo-France
  FA/grib file toolkit) — must be initialized via `epygram.init_env()`.
- `xarray`, `pandas`, `numpy`.

The shebang line (`#!/home/gmgec/mrgo/lenobler/miniforge3/bin/python3`) points
to a specific conda/miniforge environment where `epygram` is installed. If you
run this on another machine or as another user, either:
- run it explicitly with the right interpreter:
  `/path/to/env/bin/python3 create_emission_date.py`, or
- update the shebang and run `./create_emission_date.py` directly.

## Configuration

Before running, edit the top of `create_emission_date.py`:

- `date`: target date (the script picks, per dataset, the closest available
  time step — it does not interpolate).
- `prep_file_path`: input reference FA file (defines the output geometry).
- `prep_file_out`: output FA file to create (overwritten if it exists).

And `dict_var_to_treat.py` to add/remove/adjust variables. Each entry:

```python
{
    'file': '<path to NetCDF emission file>',
    'varname_nc': '<variable name inside the NetCDF file>',
    'varname_FA': '<short name used for the output FA field id>',
    'factor_conversion': <float>,  # multiplier applied before writing
}
```

## Usage

```bash
python3 create_emission_date.py
```

There are no command-line arguments — all configuration is done by editing
the script and `dict_var_to_treat.py` directly.

## Known limitations / caveats

- **Overwrite**: `prep_file_out` is silently overwritten (`shutil.copy`) on
  every run — back up the previous output first if you need to keep it.
- **Nearest-time selection only**: the script picks the closest time index
  in each dataset to `date`; it does not interpolate between time steps or
  warn if the closest match is far from the requested date.
- **Single date per run**: to process a date range, wrap the script in a
  loop over `date` values (not currently provided).
- **Environment-specific shebang**: see [Requirements](#requirements).
