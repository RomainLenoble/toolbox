# create_map_emission

Build an AROME/SURFEX "aerosol" FA file for a given date by extracting
CMIP7 emission fields (anthropogenic + open biomass burning: BC, OC, SO2)
from NetCDF datasets, regridding them onto the ALPX3 domain, and writing
them into a copy of a reference FA file (PGD or PREP).

## Files

| File | Purpose |
|---|---|
| `create_emission_date.py` | Main script: reads the reference FA geometry, extracts/regrids each configured emission variable for a target date, and writes the result to a new FA file. |
| `surfex_emission_records.py` | Writes the SURFEX metadata records (CH_EMIS, EMISNAME..., etc.) that activate the emissions; also a checker (`--check`). |
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


# Add emission to Arome/Accalmie simulation

1. Run `create_emission_date.py`. It now writes, in `PGD_file_out`:
   - the 2D fields `X001E_<name>` (BC_em, OC_em, SO2_em, BC_bb, OC_bb, SO2_bb), and
   - the SURFEX records that switch the emissions on (`surfex_emission_records.py`):
     `SFX.CH_EMIS`=.TRUE., `CH_EMIS_OPT`='AGGR', `EMISFILE_NBR`, `EMISPEC_NBR`,
     `EMISNAMEnnn`, `EMISAREAnnn`, `EMISNBTnnn`, `EMISTIMESnnn`.
   No separate SURFEX PGD run with `NAM_CH_EMIS_PGD` is needed any more. Without these
   records SURFEX does not call `CH_INIT_EMISSION_n` and the emissions stay at 0.
   Check any PGD with `python3 surfex_emission_records.py PGD_aer.fa --check`; add the
   records to an existing file with `python3 surfex_emission_records.py PGD_aer.fa BC_em BC_bb ...`.
   The species names in `varname_FA` must be the ones used in `ChemAeroSURFEX.nam` (max 12 characters).
2. Use this file as the SURFEX PGD (`Const.Clim.sfx`) of the run, with `LCH_SURF_EMIS=T` in `NAM_CH_SURFn`.
3. Update the file read by SURFEX, for tactic: `ChemAeroSURFEX.nam`:
  ```
    EMISUNIT
    Emission unit
    <unit>

    AGREGATION
      Schema reactionnel TACTIC
      BCHPHIL 0.2 BC_em 0.2 BC_bb
      BCHPHOB 0.8 BC_em 0.8 BC_bb
      OMHPHIL 0.5 OC_em 0.5 OC_bb
      OMHPHOB 0.5 OC_em 0.5 OC_bb
      SUL_SO4 0.05 SO2_em
      SUL_SO2 1. SO2_bb 1. SO2_em
    END_AGREGATION
  ```
  - `<unit>` is read by `BUILD_EMISSTAB_n`, which only accepts `MIX` (ppp m/s), `CON`
    (molecules/cm2/s) or `MOL` (umol/m2/day). The CMIP7 files are in kg m-2 s-1: a `KGS` case
    (conversion factor 1) must be added in `build_emisstabn.F90`; with tactic, `aro_ground_param`
    copies the SURFEX flux unchanged as kg m-2 s-1.
  - `SUL_SO4` is 5 % of the anthropogenic SO2 (`SO2_em`).



# list of files: 
path_CMIP7_FastTrack_aer_anthro = '/cnrm/mosca/USERS/nabat/DATA/EMISSIONS/AEROSOLS/NETCDF_src/CMIP7-FastTrack/aer_anthro/historical/'
version = "-em-anthro_input4MIPs_emissions_CMIP_CEDS-CMIP-2025-04-18_gn_"
date='200001-202312'

file_aer_anthro_BC  = path_CMIP7_FastTrack_aer_anthro + 'BC' + version + date + '.nc'
file_aer_anthro_OC  = path_CMIP7_FastTrack_aer_anthro + 'OC' + version + date + '.nc'
file_aer_anthro_SO2 = path_CMIP7_FastTrack_aer_anthro + 'SO2' + version + date + '.nc'
file_aer_anthro_NH3 = path_CMIP7_FastTrack_aer_anthro + 'NH3' + version + date + '.nc'

path_CMIP7_FastTrack_biomass-burning = file_path = '/cnrm/mosca/USERS/nabat/DATA/EMISSIONS/AEROSOLS/NETCDF_src/CMIP7-FastTrack/biomass-burning/historical/'
version = "_input4MIPs_emissions_CMIP_DRES-CMIP-BB4CMIP7-2-1_gn_"
date='175001-202312'

file_BC = path_CMIP7_FastTrack_aer_anthro + 'BC_' + version + "_" + date + '.nc'
file_OC = path_CMIP7_FastTrack_aer_anthro + 'OC_' + version + "_" + date + '.nc'
file_SO2 = path_CMIP7_FastTrack_aer_anthro + 'SO2_' + version + "_" + date + '.nc'

