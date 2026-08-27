#!/bin/bash
#SBATCH --job-name=era5_interp
#SBATCH --nodes=1
#SBATCH --time=02:10:00
#SBATCH --cpus-per-task=32

# --- site/environment setup: EDIT THIS to match your own account -----------
# This assumes the GL toolbox is installed at /home/gmgec/mrgo/lenobler/SAVE/code/GL in your own
# home directory. If it lives elsewhere, change this path.
source /home/gmgec/mrgo/lenobler/SAVE/code/GL/config/setenv.belenos
module load gcc/14.1.0
# Environment providing epygram, gl and ffmpeg. Edit/replace if your site
# uses a different module set.
module use ~mary/public/modulefiles
module load python/3.7.6nomkl
module load epygram
module load ffmpeg/4.4
# -----------------------------------------------------------------------------

export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1

NNODES=$SLURM_JOB_NUM_NODES

# Resolve this repo's directory so the script called below is always the
# git-tracked version next to this sbatch file, not a stray personal copy.
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# --- run parameters: EDIT per submission ------------------------------------
# INPUT/OUTPUT folders and all domain settings live in this config file.
CONFIG=$SCRIPT_DIR/config/ALPX3.yaml
# -----------------------------------------------------------------------------

python3 "$SCRIPT_DIR/interpole_current_folder_multiproc.py" \
                                    --config "$CONFIG" \
                                    --nproc "$SLURM_CPUS_PER_TASK"
