#!/home/gmgec/mrgo/lenobler/miniforge3/bin/python3
import argparse
import os
import re
import subprocess
from datetime import datetime, timedelta
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed

                
def process_file(filename_LBC, pattern_CAMS, AROME_prefix, list_date_CAMS, 
                 folder_LBC_ERA5, folder_CAMS, folder_output, 
                 CAMS_prefix, merge_exe):
    match = pattern_CAMS.search(filename_LBC)
    if not match:
        return None
    
    date_str = match.group(1)  # 'YYYYMMDD.HH00'
    dt = datetime.strptime(f"{date_str}", "%Y%m%d.%H00")

    # Compute absolute time differences
    time_diffs = np.abs(list_date_CAMS - dt)

    # Find the index of the closest datetime
    ind_closest_date = np.argmin(time_diffs)
    time_diff = time_diffs[ind_closest_date]

    # Check if the difference is less than 3 hours
    if time_diff < timedelta(hours=1):
        filename_CAMS = f"{CAMS_prefix}{list_date_CAMS[ind_closest_date].strftime('%Y%m%d.%H00')}"
        merge_filename = f"ALPX3_ERA5_CAMS_{date_str}"

        cmd = [
            merge_exe,
            "--inputs", os.path.join(folder_LBC_ERA5, AROME_prefix + date_str),
            os.path.join(folder_CAMS, filename_CAMS),
            "--output", os.path.join(folder_output, merge_filename)
        ]

        # Run subprocess
        subprocess.run(cmd, check=True)
        return f"Done: {merge_filename}"

    return None


def main():
    parser = argparse.ArgumentParser(description='Merge two folder to create output in an other folder')
    parser.add_argument('--ERA5', type=str, required=True,
                        help='Path to the ERA5 LBC directory.')
    parser.add_argument('--CAMS', type=str, required=True,
                        help='Path to the CAMS interpolated over the ALPX3 geometry arome.')
    parser.add_argument('--output', type=str, required=True,
                        help='Path to the folder.')

    args = parser.parse_args()

    # Assign arguments to variables
    folder_LBC_ERA5 = args.ERA5+'/'
    folder_CAMS = args.CAMS+'/'
    folder_output = args.output+'/'


    CAMS_prefix = 'CAMS_AROME_'
    AROME_prefix = 'ALPX3_ERA5_CAMS_'
    # AROME_prefix = ALPX3ERA5LBC

    pattern_CAMS = re.compile(r"(\d{8}.\d{4})")


    os.makedirs(folder_output, exist_ok=True)

    merge_exe = '/home/gmgec/mrgo/lenobler/SAVE/scripts/CAMS/merge_files.py'
    # merge_exe = '/home/gmgec/mrgo/lenobler/SAVE/scripts/CAMS/merge_CAMS_MMR.py'
    

    # merge all folder from LBC folder
    # get all dates from CAMS
    list_date_CAMS = []
    for filename_CAMS in os.listdir(folder_CAMS):
        if filename_CAMS.startswith(CAMS_prefix):
            match = pattern_CAMS.search(filename_CAMS)
            if match:
                date_str = match.group(1)  # 'YYYYMMDD.HH00'
                dt = datetime.strptime(f"{date_str}", "%Y%m%d.%H00")
                list_date_CAMS.append(dt)

    list_date_CAMS = np.array(list_date_CAMS)

    filenames = sorted(f for f in os.listdir(folder_LBC_ERA5) if f.startswith(AROME_prefix))

    with ProcessPoolExecutor(max_workers=16) as executor:  # adjust workers to your CPU
        futures = {
            executor.submit(process_file, f, pattern_CAMS, AROME_prefix, list_date_CAMS,
                            folder_LBC_ERA5, folder_CAMS, folder_output,
                            CAMS_prefix, merge_exe): f
            for f in filenames
        }

        for future in as_completed(futures):
            try:
                result = future.result()
                if result:
                    print(result)
            except Exception as e:
                print(f"Error processing {futures[future]}: ".join(e))


if __name__ == "__main__":
    main()