#!/usr/bin/env python3
import os
import re
import subprocess
from datetime import datetime
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed

# Path to the interpolation executable
# interpole_exe = '/home/gmgec/mrgo/lenobler/SAVE/scripts/CAMS/Interpol_CAMS_to_ALPX3_Arome_MMR.sh'
interpole_exe='/home/gmgec/mrgo/lenobler/SAVE/scripts/CAMS/Interpol_CAMS_to_ALPX3_Arome_LIMA_group.py'

def process_file(filename, input_folder, output_folder):
    """Run the interpolation for a single file"""
    pattern = re.compile(r"(\d{4}-\d{2}-\d{2}-\d{2})")
    match = pattern.search(filename)

    if not match:
        return f"Skipped {filename} (no date match)"

    date_str = match.group(1)  # 'YYYY-MM-DD-HH'
    dt = datetime.strptime(date_str, "%Y-%m-%d-%H")
    output_filename = f"CAMS_AROME_{dt.strftime('%Y%m%d.%H00')}"

    input_file = os.path.join(input_folder, filename)
    output_file = os.path.join(output_folder, output_filename)

    subprocess.run([interpole_exe, input_file, output_file], check=True)

    return f"Processed {filename} -> {output_filename}"

def interpole_folder(input_folder, output_folder, workers=8):
    files = [f for f in os.listdir(input_folder) if f.startswith("CAMS_ALPX3_2012")]

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(process_file, f, input_folder, output_folder): f
            for f in files
        }

        for future in as_completed(futures):
            try:
                print(future.result())
            except Exception as e:
                print(f"Error with {futures[future]}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interpolate CAMS files to ALPX3 Arome format")
    parser.add_argument("input_folder", help="Path to the input folder containing CAMS files")
    parser.add_argument("output_folder", help="Path to the output folder where results will be saved")
    parser.add_argument("--workers", type=int, default=10, help="Number of parallel workers (default: 10)")
    args = parser.parse_args()

    os.makedirs(args.output_folder, exist_ok=True)
    interpole_folder(args.input_folder, args.output_folder, args.workers)