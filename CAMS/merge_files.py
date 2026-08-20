#!/usr/bin/env python3

import argparse
import shutil
import epygram

# Initialize epygram environment
epygram.init_env()

# ---------------------------   
# Argument parser
# ---------------------------
parser = argparse.ArgumentParser(description="Merge GRIB/FA files into a single one.")
parser.add_argument(
    "--inputs",
    type=str,
    nargs="+",
    required=True,
    help="List of input GRIB/FA files."
)
parser.add_argument(
    "--output",
    type=str,
    required=True,
    help="Path to the merged output file."
)

args = parser.parse_args()

INPUTS = args.inputs
OUTPUT = args.output

# ---------------------------
# Initialize output file by copying the first one
# ---------------------------
shutil.copy(INPUTS[0], OUTPUT)

FA_output = epygram.formats.resource(OUTPUT, "a")

# ---------------------------
# Loop over all input files
# ---------------------------
for infile in INPUTS[1:]:
    FA_in = epygram.formats.resource(infile, "r")

    for key in FA_in.listfields():
        if "DUMMY" in key:
            continue
        field_value = FA_in.readfield(key)
        FA_output.writefield(field_value)

    FA_in.close()

FA_output.close()
