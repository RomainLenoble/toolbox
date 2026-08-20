#!/home/gmgec/mrgo/lenobler/miniforge3/bin/python3
import argparse
import os
import re
import subprocess
from datetime import datetime, timedelta
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed
import sys

def run_in_env(command):
    """
    Run a shell command after sourcing the Belenos environment and with_epygram_old.
    """
    env_setup = "source /home/gmgec/mrgo/lenobler/SAVE/code/GL/config/setenv.belenos && . with_epygram_old"
    full_cmd = f"bash -c 'ulimit -s unlimited && {env_setup} && {command}'"
    subprocess.run(full_cmd, shell=True, check=True)
          
def main():
    parser = argparse.ArgumentParser(description='Merge two folder to create output in an other folder')
    parser.add_argument('--ERA5', type=str, required=True,
                        help='Path to the ERA5 LBC directory.')
    parser.add_argument('--CAMS', type=str, required=True,
                        help='Path to the CAMS interpolated over the ALPX3 geometry arome.')
    parser.add_argument('--mode', type=str, required=True,
                        help='aerosol properties, see lima_utils to choose the mode')
    parser.add_argument('--output', type=str, required=True,
                        help='Path to the output folder.')

    args = parser.parse_args()

    # Assign arguments to variables
    folder_LBC_ERA5 = os.path.abspath(args.ERA5)
    folder_CAMS = os.path.abspath(args.CAMS)
    folder_output = os.path.abspath(args.output)

    # create folder for interpolated CAMS data
    basename_CAMS = os.path.basename(os.path.normpath(folder_CAMS))
    folder_temp = os.path.join(folder_output, f"{folder_output}/tmp_interp/")

    # make sure the folder exists
    os.makedirs(folder_temp, exist_ok=True)


    # ---------------------------------------------------
    # Interpolate CAMS data to Arome grid
    # ---------------------------------------------------
    interpole_exe = '/home/gmgec/mrgo/lenobler/SAVE/scripts/CAMS/interpole_current_folder.py'
    run_in_env(f"{interpole_exe} --input_folder {folder_CAMS} --output_folder {folder_temp} --mode {args.mode}")

    # ---------------------------------------------------
    # Interpolate in time (create missing times) in CAMS
    # ---------------------------------------------------
    interpolate_grib_hourly_epygram='/home/gmgec/mrgo/lenobler/SAVE/scripts/CAMS/interpolate_grib_hourly_epygram.py'
    run_in_env(f"{interpolate_grib_hourly_epygram} --input_folder {folder_temp}")
    
    # ---------------------------------------------------
    # Merge the CAMS and Arome files
    # ---------------------------------------------------
    merge_exe = '/home/gmgec/mrgo/lenobler/SAVE/scripts/CAMS/merge_LBC.py'
    run_in_env(f"{merge_exe} --ERA5 {folder_LBC_ERA5} --CAMS {folder_temp} --output {folder_output}")

    # clean directory and keep history
    os.rename('naminterp', f"{folder_output}/naminterp")
    os.remove('climate_aladin')
    # Reconstruct the command
    command = ' '.join([sys.executable] + sys.argv)

    # Optional: log file path
    log_file = "command_history.log"

    # Append the command to the log with timestamp
    with open(log_file, 'a') as f:
        f.write(f"{datetime.now()} : {command}\n")
    os.rename(f'{log_file}', f"{folder_output}/{log_file}")

if __name__ == "__main__":
    main()