"""
dict_var_to_treat.py

Defines `variable_to_treat`: the list of emission variables that
`create_emission_date.py` extracts and writes into the output FA file.

Each entry is a dict with:
    'file'                : path to the source NetCDF emission dataset.
    'varname_nc'           : name of the variable to read inside that
                              NetCDF file (as seen by epygram/xarray).
    'varname_FA'           : short name used to build the output FA field
                              id (prefixed with FA_FIELD_PREFIX, see
                              create_emission_date.py).
    'factor_conversion'    : multiplicative factor applied to the raw
                              NetCDF values before writing them out
                              (e.g. unit conversion, species scaling).

Two emission inventories are combined here:
    - CMIP7-FastTrack anthropogenic emissions (aer_anthro).
    - CMIP7-FastTrack open biomass-burning emissions (biomass-burning).
"""

variable_to_treat = []

# --- Anthropogenic emissions (CEDS, via CMIP7-FastTrack) ---
path_CMIP7_FastTrack_aer_anthro = '/scratch/work/lenobler/DATA/CMIP7-FastTrack/aer_anthro/historical/'
version = "-em-anthro_input4MIPs_emissions_CMIP_CEDS-CMIP-2025-04-18_gn_"
date_span = '200001-202312'


variable_to_treat += [
    {'file': path_CMIP7_FastTrack_aer_anthro + 'BC' + version + date_span + '.nc',
     'varname_nc': 'BC_em_anthro',
     'varname_FA': 'BC_em',
     'factor_conversion': 1.7
     },

    {'file': path_CMIP7_FastTrack_aer_anthro + 'OC' + version + date_span + '.nc',
     'varname_nc': 'OC_em_anthro',
     'varname_FA': 'OC_em',
     'factor_conversion': 1.5
     },

    {'file': path_CMIP7_FastTrack_aer_anthro + 'SO2' + version + date_span + '.nc',
     'varname_nc': 'SO2_em_anthro',
     'varname_FA': 'SO2_e',
     'factor_conversion': 1
     },

    # NH3 anthropogenic emissions: disabled, not currently needed downstream.
    # {'file' : path_CMIP7_FastTrack_aer_anthro + 'NH3' + version + date_span + '.nc',
    #  'varname_nc' : 'NH3_em_anthro',
    #  'varname_FA' : 'NH3_em',
    #  'factor_conversion' : 1
    # },
]

# --- Open biomass-burning emissions (BB4CMIP7, via CMIP7-FastTrack) ---
path_CMIP7_FastTrack_biomass_burning = '/scratch/work/lenobler/DATA/CMIP7-FastTrack/biomass-burning/historical/'
version = "_input4MIPs_emissions_CMIP_DRES-CMIP-BB4CMIP7-2-1_gn_"
date_span = '190001-202312'

variable_to_treat += [

    {'file': path_CMIP7_FastTrack_biomass_burning + 'BC' + version + date_span + '.nc',
     'varname_nc': 'BC',
     'varname_FA': 'BC_bb',
     'factor_conversion': 1.5
     },

    {'file': path_CMIP7_FastTrack_biomass_burning + 'OC' + version + date_span + '.nc',
     'varname_nc': 'OC',
     'varname_FA': 'OC_bb',
     'factor_conversion': 1.5
     },

    {'file': path_CMIP7_FastTrack_biomass_burning + 'SO2' + version + date_span + '.nc',
     'varname_nc': 'SO2',
     'varname_FA': 'SO2_bb',
     'factor_conversion': 1
     },
]
