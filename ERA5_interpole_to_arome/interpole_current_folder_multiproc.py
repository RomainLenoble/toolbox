#!/usr/bin/env python3
import os
import re
from datetime import datetime
import argparse
import numpy as np
from multiprocessing import Pool

from interpole_era5_to_ALPX3 import interpole_file, load_config


def process_file(args):
    input_folder, output_folder, filename, config = args

    input_files = config["input_files"]
    pattern = re.compile(input_files["date_regex"])

    match = pattern.search(filename)
    if not match:
        return

    date_str = match.group(1)
    dt = datetime.strptime(date_str, input_files["date_format"])

    output_filename = config["domain"]["output_pattern"].format(
        name=config["domain"]["name"], date=dt.strftime("%Y%m%d.%H00")
    )

    input_file = os.path.join(input_folder, filename)
    output_file = os.path.join(output_folder, output_filename)

    print(f"Processing {input_file} -> {output_file}")

    interpole_file(input_file, output_file, config)


def interpole_folder(input_folder, output_folder, nproc, config):

    input_files = config["input_files"]
    files = [
        f for f in np.sort(os.listdir(input_folder))
        if f.startswith(input_files["prefix"])
        and not f.endswith(input_files["exclude_suffix"])
    ]

    tasks = [(input_folder, output_folder, f, config) for f in files]

    with Pool(processes=nproc) as pool:
        pool.map(process_file, tasks)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Interpolate ERA5 files to a target domain (GL)"
    )
    parser.add_argument(
        "--input_folder",
        type=str,
        default=None,
        help="Overrides paths.input_folder from --config",
    )
    parser.add_argument(
        "--output_folder",
        type=str,
        default=None,
        help="Overrides paths.output_folder from --config",
    )
    parser.add_argument("--nproc", type=int, default=os.cpu_count())
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to the domain YAML config (see config/ALPX3.yaml)",
    )

    args = parser.parse_args()

    config = load_config(args.config)

    input_folder = args.input_folder or config["paths"]["input_folder"]
    output_folder = args.output_folder or config["paths"]["output_folder"]

    os.makedirs(output_folder, exist_ok=True)

    interpole_folder(input_folder, output_folder, args.nproc, config)
