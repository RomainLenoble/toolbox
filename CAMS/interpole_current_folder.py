#!/home/gmgec/mrgo/lenobler/miniforge3/bin/python3
import os
import re
import subprocess
from datetime import datetime
import argparse
from Interpol_CAMS_to_ALPX3 import interpole_file
from lbc_config import load_config


def interpole_folder(input_folder, output_folder, config, all_particles, list_FA_name):
    prefix = config["naming"]["cams_input_prefix"]
    pattern = re.compile(config["naming"]["cams_input_datetime_regex"])
    dt_format = config["naming"]["cams_input_datetime_format"]
    interp_prefix = config["naming"]["cams_interp_prefix"]

    for filename in os.listdir(input_folder):
        if filename.startswith(prefix):
            match = pattern.search(filename)
            if match:
                date_str = match.group(1)  # 'YYYY-MM-DD-HH'
                dt = datetime.strptime(date_str, dt_format)
                output_filename = f"{interp_prefix}{dt.strftime('%Y%m%d.%H00')}"

                input_file = os.path.join(input_folder, filename)
                output_file = os.path.join(output_folder, output_filename)

                print(f"Processing {input_file} -> {output_file}")
                interpole_file(
                    input_file, output_file, all_particles,
                    list_FA_name=list_FA_name, config=config, work_dir='./',
                )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interpolate CAMS files to the target Arome domain")
    parser.add_argument("--input_folder", type=str, required=True, help="Path to the input folder containing CAMS files")
    parser.add_argument("--output_folder", type=str, required=True, help="Path to the output folder where results will be saved")
    parser.add_argument("--mode", type=str, required=True, help="aerosol properties, see lima_utils to choose the values")
    parser.add_argument("--config", type=str, required=True, help="Path to the YAML config file (see config/ALPX3.yaml)")
    args = parser.parse_args()

    config = load_config(args.config)

    os.makedirs(args.output_folder, exist_ok=True)

    #####################
    # Select aerosol mode
    #####################
    if args.mode.lower() == 'mmr':
        all_particles = []
        list_FA_name = config["aerosols"]["mmr_faname"]
    else:
        import lib.lima_utils as lu
        all_particles = lu.get_scaling_aerosol(case=args.mode, GL_interp=True)  
        list_group = [[aer_specie['faname']]*len(aer_specie['shortname']) for aer_specie in all_particles]
        list_FA_name = [j for i in list_group for j in i]


    interpole_folder(args.input_folder, args.output_folder, config, all_particles, list_FA_name)