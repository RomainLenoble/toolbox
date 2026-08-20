#!/home/gmgec/mrgo/lenobler/miniforge3/bin/python3
"""
create_emission_date.py

Build an AROME/SURFEX "aerosol" FA file for a single date by extracting
CMIP7 anthropogenic and biomass-burning emission fields (BC, OC, SO2, ...)
from NetCDF datasets, regridding them onto the ALPX3 domain, and writing
them as new fields into a copy of a reference FA file (PGD or PREP).

Workflow:
    1. Open the reference FA file to get the target ALPX3 geometry.
    2. Copy that file so the new fields can be appended to it.
    3. For each variable described in `dict_var_to_treat.variable_to_treat`:
        a. Open the source NetCDF file with xarray (to inspect time/sector
           coordinates) and with epygram (to read/regrid the field).
        b. Find the time index closest to `date`.
        c. Sum over emission sectors if the variable has a 'sector' dimension.
        d. Regrid ("extract_subdomain") onto the reference geometry.
        e. Mask unphysical values, apply the variable's unit-conversion
           factor, and write the field into the output FA file.

Configuration (edit as needed before running):
    - `date`: the target date to extract from each emission dataset.
    - `PGD_file_path` / `PGD_file_out`: input reference file and output
      file to create.
    - `dict_var_to_treat.variable_to_treat`: list of variables to process.

Requires an environment with epygram, xarray, pandas and numpy installed
(see README.md for details).
"""
import numpy as np
import xarray as xr
import pandas as pd
import epygram
import shutil

epygram.init_env()
import dict_var_to_treat

# Target date: the script picks, for each emission dataset, the time step
# closest to this date.
date = pd.to_datetime('2012/10/17', format='%Y/%m/%d')

# --- Reference file (defines the output geometry) and output file ---
# Alternative reference: a PREP restart file instead of the PGD file.
# PGD_file_path = '/scratch/work/lenobler/DATA/ALPX3/restart/sfx/PREP.ALPX3.cy49_201210170000.fa'
# PGD_file_out  = '/scratch/work/lenobler/DATA/ALPX3/restart/sfx/PREP.ALPX3.cy49_201210170000_aerosol.fa'

PGD_file_path = '/scratch/work/lenobler/CLIMAKE/outputFiles/cy49_tactic_emis/PGD_aerosol.fa'
PGD_file_out = '/scratch/work/lenobler/CLIMAKE/outputFiles/cy49_tactic_emis/PGD_aerosol_1.fa'

# Prefix prepended to every field name written to the output FA file
# (arbitrary FA "experiment" tag used to namespace these fields).
FA_FIELD_PREFIX = 'X001E_'

prep_file = epygram.open(PGD_file_path, 'r')
try:
    # Read any 2D field just to get hold of the ALPX3 geometry.
    f_arome = prep_file.readfield('SFX.COVER001')
except Exception:
    # Fallback in case COVER001 isn't in this particular file (e.g. PREP
    # files may not carry it) - Z0WATER is expected to always be present.
    # NOTE: kept broad on purpose (unsure of epygram's exact exception
    # type for "field not found"); narrow this down if you know it.
    f_arome = prep_file.readfield('SFX.Z0WATER')
prep_file.close()

# shutil.copy overwrites PGD_file_out if it already exists.
shutil.copy(PGD_file_path, PGD_file_out)
prep_out = epygram.open(PGD_file_out, 'a')

for variable in dict_var_to_treat.variable_to_treat:

    print(variable)
    file_path = variable['file']
    varname_nc = variable['varname_nc']
    varname_FA = variable['varname_FA']
    factor_conversion = variable['factor_conversion']

    # Read the emission file both with epygram (regridding) and xarray
    # (convenient access to the time/sector coordinates).
    r = epygram.open(file_path, 'r')
    ds = xr.open_dataset(file_path)

    ########
    # Get index of the time step closest to `date`
    ########
    time_values = ds.time.values

    target = time_values[0].__class__(date.year, date.month, date.day)

    idx = np.abs(time_values - target).argmin()
    print(f"find date : {ds.time[idx].values}")

    f_new = f_arome.copy()
    data = f_new.getdata() * 0.

    if 'sector' in list(ds.coords):
        # Emission is split across several sectors (e.g. energy, transport,
        # residential, ...): sum them to get the total emission.
        for id_sector in range(len(ds.sector)):
            f_idx = r.readfield(varname_nc, only={'time': int(idx), 'sector': id_sector})
            f_idx_alpx3 = f_idx.extract_subdomain(f_arome.geometry)
            data += f_idx_alpx3.getdata()
    else:
        # Single field for this date: regrid onto the ALPX3 domain directly.
        f_idx = r.readfield(varname_nc, only={'time': int(idx)})
        f_idx_alpx3 = f_idx.extract_subdomain(f_arome.geometry)
        data = f_idx_alpx3.getdata()

    # Discard unphysical values (outside epygram's configured valid range)
    # before converting units.
    data_filter = np.ma.masked_outside(data,
                                        - epygram.config.mask_outside,
                                        epygram.config.mask_outside)

    f_new.setdata(data_filter * factor_conversion)

    f_new.fid['FA'] = FA_FIELD_PREFIX + varname_FA

    prep_out.writefield(f_new)

    r.close()
    ds.close()

prep_out.close()
