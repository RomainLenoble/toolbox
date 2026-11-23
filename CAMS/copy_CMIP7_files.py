#!/usr/bin/env python3
"""Copy the CMIP7 FastTrack emission files to another machine, keeping the folder structure.

Usage: copy_CMIP7_files.py [user@]host:/dest/dir
  -> /dest/dir/cnrm/mosca/USERS/.../aer_anthro/historical/BC-em-anthro_...nc
Run it on the machine that holds the files.
"""
import subprocess
import sys

path_CMIP7_FastTrack_aer_anthro = '/cnrm/mosca/USERS/nabat/DATA/EMISSIONS/AEROSOLS/NETCDF_src/CMIP7-FastTrack/aer_anthro/historical/'
version = "-em-anthro_input4MIPs_emissions_CMIP_CEDS-CMIP-2025-04-18_gn_"
date = '200001-202312'

file_aer_anthro_BC  = path_CMIP7_FastTrack_aer_anthro + 'BC' + version + date + '.nc'
file_aer_anthro_OC  = path_CMIP7_FastTrack_aer_anthro + 'OC' + version + date + '.nc'
file_aer_anthro_SO2 = path_CMIP7_FastTrack_aer_anthro + 'SO2' + version + date + '.nc'
file_aer_anthro_NH3 = path_CMIP7_FastTrack_aer_anthro + 'NH3' + version + date + '.nc'

path_CMIP7_FastTrack_biomass_burning = '/cnrm/mosca/USERS/nabat/DATA/EMISSIONS/AEROSOLS/NETCDF_src/CMIP7-FastTrack/biomass-burning/historical/'
version = "_input4MIPs_emissions_CMIP_DRES-CMIP-BB4CMIP7-2-1_gn_"
date = '175001-202312'

file_BC  = path_CMIP7_FastTrack_biomass_burning + 'BC' + version + date + '.nc'
file_OC  = path_CMIP7_FastTrack_biomass_burning + 'OC' + version + date + '.nc'
file_SO2 = path_CMIP7_FastTrack_biomass_burning + 'SO2' + version + date + '.nc'

files = [file_aer_anthro_BC, file_aer_anthro_OC, file_aer_anthro_SO2, file_aer_anthro_NH3,
         file_BC, file_OC, file_SO2]

if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    dest = sys.argv[1]
    # -R (--relative) recreates the full source path under dest; rsync goes over ssh like scp
    subprocess.run(['rsync', '-avR', '--progress'] + files + [dest], check=True)
