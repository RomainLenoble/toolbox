#!/home/gmgec/mrgo/lenobler/miniforge3/bin/python3
import numpy as np
import xarray as xr
import pandas as pd
import epygram
import os
import shutil
epygram.init_env()
import dict_var_to_treat

date = pd.to_datetime('2012/10/17', format='%Y/%m/%d')

prep_file_path = '/scratch/work/lenobler/DATA/ALPX3/restart/sfx/PREP.ALPX3.cy49_201210170000.fa'
prep_file_out  = '/scratch/work/lenobler/DATA/ALPX3/restart/sfx/PREP.ALPX3.cy49_201210170000_aerosol.fa'

prep_file_path='/scratch/work/lenobler/CLIMAKE/outputFiles/cy49_tactic_emis/PGD.fa'
prep_file_out='/scratch/work/lenobler/CLIMAKE/outputFiles/cy49_tactic_emis/PGD_aerosol.fa'


prep_file = epygram.open(prep_file_path, 'r')
try:
    f_arome = prep_file.readfield('SFX.COVER001') # read any fiel to get the geometry
except:
    f_arome = prep_file.readfield('SFX.Z0WATER') # read any fiel to get the geometry


shutil.copy(prep_file_path, prep_file_out)
prep_out = epygram.open(prep_file_out, 'a')


for variable in dict_var_to_treat.variable_to_treat:

    print(variable)
    file_path = variable['file']
    varname_nc = variable['varname_nc']
    varname_FA = variable['varname_FA']
    factor_conversion = variable['factor_conversion']
    
    # Read emission file with epygram and xarray
    r = epygram.open(file_path, 'r')
    ds = xr.open_dataset(file_path)


    ########
    # Get indice closest to date
    ########
    time_values = ds.time.values

    target = time_values[0].__class__(date.year, date.month, date.day)

    idx = np.abs(time_values - target).argmin()
    print(f"find date : {ds.time[idx].values}")

    f_new = f_arome.copy()
    data = f_new.getdata() * 0.

    if 'sector' in list(ds.coords):
        for id_sector in range(len(ds.sector)):
            f_idx = r.readfield(varname_nc, only={'time':int(idx), 'sector':id_sector})
            f_idx_alpx3 = f_idx.extract_subdomain(f_arome.geometry)
            data += f_idx_alpx3.getdata()

    else:
        # Extract the date in epygram
        f_idx = r.readfield(varname_nc, only={'time':int(idx)})
        f_idx_alpx3 = f_idx.extract_subdomain(f_arome.geometry)
        data = f_idx_alpx3.getdata()

    data_filter = np.ma.masked_outside(data,
                            - epygram.config.mask_outside,
                            epygram.config.mask_outside)

    f_new.setdata(data_filter * factor_conversion)
    # f_new.setdata(np.ones_like(data_filter))

    f_new.fid['FA'] = 'X001E_' + varname_FA

    prep_out.writefield(f_new)

prep_out.close()