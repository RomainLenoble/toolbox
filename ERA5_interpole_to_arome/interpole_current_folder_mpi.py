#!/home/gmgec/mrgo/lenobler/miniforge3/bin/python3
import os
import re
from datetime import datetime
import argparse
import numpy as np
from mpi4py import MPI

from interpole_era5_to_ALPX3 import interpole_file


def interpole_folder(input_folder, output_folder, rank, size):

    pattern = re.compile(r"(\d{8}_\d{2})")

    files = [
        f for f in np.sort(os.listdir(input_folder))
        if f.startswith("era5_2") and not f.endswith(".info")
    ]

    # distribute files among ranks
    files_local = files[rank::size]

    for filename in files_local:

        match = pattern.search(filename)
        if not match:
            continue

        date_str = match.group(1)
        dt = datetime.strptime(date_str, "%Y%m%d_%H")

        output_filename = f"ALPX3ERA5LBC{dt.strftime('%Y%m%d.%H00')}"

        input_file = os.path.join(input_folder, filename)
        output_file = os.path.join(output_folder, output_filename)

        print(f"[Rank {rank}] Processing {input_file} -> {output_file}")

        interpole_file(input_file, output_file)


if __name__ == "__main__":

    # MPI init
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()

    parser = argparse.ArgumentParser(
        description="Interpolate ERA5 files to ALPX3 Arome format"
    )
    parser.add_argument("--input_folder", type=str, required=True)
    parser.add_argument("--output_folder", type=str, required=True)

    args = parser.parse_args()

    if rank == 0:
        os.makedirs(args.output_folder, exist_ok=True)

    # wait for folder creation
    comm.Barrier()

    interpole_folder(args.input_folder, args.output_folder, rank, size)
