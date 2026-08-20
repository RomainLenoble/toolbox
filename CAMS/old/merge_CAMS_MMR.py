#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import epygram
import numpy as np
import warnings
import argparse
import os
import shutil
import sys

# Suppress warnings
warnings.filterwarnings('ignore')

# Initialize epygram environment
epygram.init_env()

# Set up argument parser
parser = argparse.ArgumentParser(description='Process aerosol and AROME restart files.')
parser.add_argument('--cams', type=str, required=True,
                    help='Path to the CAMS aerosol GRIB file.')
parser.add_argument('--arome', type=str, required=True,
                    help='Path to the AROME restart file.')
parser.add_argument('--output', type=str, required=True,
                    help='Path to the output file after conversion.')

args = parser.parse_args()

# Assign arguments to variables
CAMS = args.cams
AROME = args.arome
Output = args.output


shutil.copy(AROME, Output)

NBLEV=60

list_field_name = ['SEASALT1','SEASALT2','SEASALT3','DUST1','DUST2','DUST3','OM1','OM2','BC1','BC2','SULF']

for l in range(1,NBLEV+1):
    iLev = str(l)
    while len(iLev) < 3:
        iLev = "0" + iLev
    ### ==
    ### LECTURE FICHIER AEROSOLS
    FA_CAMS = epygram.formats.resource(CAMS, 'r')
    
    list_field = []
    for field_name in list_field_name:
        CAMS_field = FA_CAMS.readfield('S'+iLev+field_name)
        CAMS_field.operation('*', 100) 
        list_field.append(CAMS_field)
    FA_CAMS.close()
    ### ==
    ### FICHIER CPL
    FA_CPL = epygram.formats.resource(Output, 'a')
    for field in list_field:        
        FA_CPL.writefield(field)
    FA_CPL.close()
