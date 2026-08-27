#!/home/gmgec/mrgo/lenobler/miniforge3/bin/python3
import os
import re
from datetime import datetime
import argparse
import numpy as np
from multiprocessing import Pool

from interpole_era5_to_ALPX3 import interpole_file


pattern = re.compile(r"(\d{8}_\d{2})")


def process_file(args):
    input_folder, output_folder, filename = args

    match = pattern.search(filename)
    if not match:
        return

    date_str = match.group(1)
    dt = datetime.strptime(date_str, "%Y%m%d_%H")

    output_filename = f"ALPX3ERA5LBC{dt.strftime('%Y%m%d.%H00')}"

    input_file = os.path.join(input_folder, filename)
    output_file = os.path.join(output_folder, output_filename)

    print(f"Processing {input_file} -> {output_file}")

    interpole_file(input_file, output_file)


def interpole_folder(input_folder, output_folder, nproc):

    files = [
        f for f in np.sort(os.listdir(input_folder))
        if f.startswith("era5_2") and not f.endswith(".info")
    ]

    tasks = [(input_folder, output_folder, f) for f in files]

    with Pool(processes=nproc) as pool:
        pool.map(process_file, tasks)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Interpolate ERA5 files to ALPX3 Arome format"
    )
    parser.add_argument("--input_folder", type=str, required=True)
    parser.add_argument("--output_folder", type=str, required=True)
    parser.add_argument("--nproc", type=int, default=os.cpu_count())

    args = parser.parse_args()

    os.makedirs(args.output_folder, exist_ok=True)

    interpole_folder(args.input_folder, args.output_folder, args.nproc)