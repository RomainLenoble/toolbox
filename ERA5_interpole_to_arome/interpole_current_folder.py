#!/home/gmgec/mrgo/lenobler/miniforge3/bin/python3
import os
import re
import subprocess
from datetime import datetime
import argparse
from interpole_era5_to_ALPX3 import interpole_file
import numpy as np

def interpole_folder(input_folder, output_folder):
    pattern = re.compile(r"(\d{4}\d{2}\d{2}_\d{2})")

    for filename in np.sort(os.listdir(input_folder)):
        if filename.startswith('era5_2'):
            match = pattern.search(filename)
            if match:
                date_str = match.group(1)  # 'YYYY-MM-DD-HH'
                dt = datetime.strptime(date_str, "%Y%m%d_%H")
                output_filename = f"ALPX3ERA5LBC{dt.strftime('%Y%m%d.%H00')}"

                input_file = os.path.join(input_folder, filename)
                output_file = os.path.join(output_folder, output_filename)

                print(f"Processing {input_file} -> {output_file}")
                interpole_file(input_file, output_file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interpolate CAMS files to ALPX3 Arome format")
    parser.add_argument("--input_folder", type=str, required=True, help="Path to the input folder containing CAMS files")
    parser.add_argument("--output_folder", type=str, required=True, help="Path to the output folder where results will be saved")
    args = parser.parse_args()


    os.makedirs(args.output_folder, exist_ok=True)



    interpole_folder(args.input_folder, args.output_folder)