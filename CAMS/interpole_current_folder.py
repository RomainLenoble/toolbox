#!/home/gmgec/mrgo/lenobler/miniforge3/bin/python3
import os
import re
import subprocess
from datetime import datetime
import argparse
from Interpol_CAMS_to_ALPX3 import interpole_file


def interpole_folder(input_folder, output_folder):
    pattern = re.compile(r"(\d{4}-\d{2}-\d{2}-\d{2})")

    for filename in os.listdir(input_folder):
        if filename.startswith('CAMS_ALPX3_2012'):
            match = pattern.search(filename)
            if match:
                date_str = match.group(1)  # 'YYYY-MM-DD-HH'
                dt = datetime.strptime(date_str, "%Y-%m-%d-%H")
                output_filename = f"CAMS_AROME_{dt.strftime('%Y%m%d.%H00')}"

                input_file = os.path.join(input_folder, filename)
                output_file = os.path.join(output_folder, output_filename)

                print(f"Processing {input_file} -> {output_file}")
                interpole_file(input_file, output_file, all_particles, list_FA_name=list_FA_name)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interpolate CAMS files to ALPX3 Arome format")
    parser.add_argument("--input_folder", type=str, required=True, help="Path to the input folder containing CAMS files")
    parser.add_argument("--output_folder", type=str, required=True, help="Path to the output folder where results will be saved")
    parser.add_argument("--mode", type=str, required=True, help="aerosol properties, see lima_utils to choose the values")
    args = parser.parse_args()


    os.makedirs(args.output_folder, exist_ok=True)

    #####################
    # Select aerosol mode
    #####################
    if args.mode == 'MMR':
        all_particles = []
        list_FA_name = ['SEASALT1_MMR','SEASALT2_MMR','SEASALT3_MMR','DUST1_MMR','DUST2_MMR','DUST3_MMR','OM1_MMR','OM2_MMR','BC1_MMR','BC2_MMR','SULF_MMR']
    else:
        import lib.lima_utils as lu
        all_particles = lu.get_scaling_aerosol(case=args.mode, GL_interp=True)  
        list_group = [[aer_specie['faname']]*len(aer_specie['shortname']) for aer_specie in all_particles]
        list_FA_name = [j for i in list_group for j in i]


    interpole_folder(args.input_folder, args.output_folder)