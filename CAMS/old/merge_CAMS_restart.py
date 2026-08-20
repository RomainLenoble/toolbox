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
parser = argparse.ArgumentParser(description='Merge GRIB/FA files in a single one.')
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

FA_CAMS = epygram.formats.resource(CAMS, 'r')
FA_output = epygram.formats.resource(Output, 'a')

for key in FA_CAMS.listfields():
    if 'DUMMY' in key:
        continue
    field_value = FA_CAMS.readfield(key)
    FA_output.writefield(field_value)

FA_CAMS.close()
FA_output.close()