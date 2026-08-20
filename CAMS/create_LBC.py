#!/usr/bin/env python3
import argparse
import os
import re
import subprocess
from datetime import datetime, timedelta
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed
import sys

from lbc_config import load_config

def run_in_env(command, env_setup):
    """
    Run a shell command, optionally after sourcing the environment defined
    in the config file (paths.env_setup).
    """
    if env_setup:
        full_cmd = f"bash -c 'ulimit -s unlimited && {env_setup} && {command}'"
    else:
        full_cmd = f"bash -c 'ulimit -s unlimited && {command}'"
    subprocess.run(full_cmd, shell=True, check=True)
          
def main():
    parser = argparse.ArgumentParser(description='Merge two folder to create output in an other folder')
    parser.add_argument('--ERA5', type=str, required=True,
                        help='Path to the ERA5 LBC directory.')
    parser.add_argument('--CAMS', type=str, required=True,
                        help='Path to the CAMS interpolated over the target geometry Arome.')
    parser.add_argument('--mode', type=str, required=True,
                        help='aerosol properties, see lima_utils to choose the mode')
    parser.add_argument('--output', type=str, required=True,
                        help='Path to the output folder.')
    parser.add_argument('--config', type=str, required=True,
                        help='Path to the YAML config file (domain/paths/naming/runtime parameters). '
                             'See config/ALPX3.yaml for a documented example.')

    args = parser.parse_args()

    config = load_config(args.config)
    config_path = os.path.abspath(args.config)
    scripts_dir = config["paths"]["scripts_dir"]
    env_setup = config["paths"]["env_setup"]

    # Assign arguments to variables
    folder_LBC_ERA5 = os.path.abspath(args.ERA5)
    folder_CAMS = os.path.abspath(args.CAMS)
    folder_output = os.path.abspath(args.output)

    # create folder for interpolated CAMS data
    folder_temp = os.path.join(folder_output, "tmp_interp")

    # make sure the folder exists
    os.makedirs(folder_temp, exist_ok=True)


    # ---------------------------------------------------
    # Interpolate CAMS data to Arome grid
    # ---------------------------------------------------
    interpole_exe = os.path.join(scripts_dir, "interpole_current_folder.py")
    run_in_env(
        f"{interpole_exe} --input_folder {folder_CAMS} --output_folder {folder_temp} "
        f"--mode {args.mode} --config {config_path}",
        env_setup,
    )

    # ---------------------------------------------------
    # Interpolate in time (create missing times) in CAMS
    # ---------------------------------------------------
    interpolate_grib_hourly_epygram = os.path.join(scripts_dir, "interpolate_grib_hourly_epygram.py")
    run_in_env(
        f"{interpolate_grib_hourly_epygram} --input_folder {folder_temp} --config {config_path}",
        env_setup,
    )
    
    # ---------------------------------------------------
    # Merge the CAMS and Arome files
    # ---------------------------------------------------
    merge_exe = os.path.join(scripts_dir, "merge_LBC.py")
    run_in_env(
        f"{merge_exe} --ERA5 {folder_LBC_ERA5} --CAMS {folder_temp} --output {folder_output} "
        f"--config {config_path}",
        env_setup,
    )

    # clean directory and keep history
    # (naminterp/climate_aladin are created by interpole_file() inside folder_temp)
    naminterp_path = os.path.join(folder_temp, "naminterp")
    climate_link_path = os.path.join(folder_temp, "climate_aladin")
    if os.path.exists(naminterp_path):
        os.rename(naminterp_path, os.path.join(folder_output, "naminterp"))
    if os.path.islink(climate_link_path) or os.path.exists(climate_link_path):
        os.remove(climate_link_path)

    # Reconstruct the command
    command = ' '.join([sys.executable] + sys.argv)

    # Append the command to the log with timestamp
    log_path = os.path.join(folder_output, "command_history.log")
    with open(log_path, 'a') as f:
        f.write(f"{datetime.now()} : {command}\n")

if __name__ == "__main__":
    main()