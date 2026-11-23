#!/bin/bash
#SBATCH --job-name=create_LBC
#SBATCH --nodes=1
#SBATCH --time=15:00:00
#SBATCH --cpus-per-task=32
#SBATCH -p shared

# Same environment as ERA5_interpole_to_arome/sbatch_interpole_multiproc.sh
source /home/gmgec/mrgo/lenobler/SAVE/code/GL/config/setenv.belenos
module load gcc/14.1.0
module use ~mary/public/modulefiles
module load python/3.7.6nomkl
module load epygram
module load ffmpeg/4.4

export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
ulimit -s unlimited

export PYTHONUNBUFFERED=1

# --- run parameters: EDIT per submission ------------------------------------
TOOLBOX=/home/gmgec/mrgo/lenobler/SAVE/code/toolbox
ERA5=/scratch/work/lenobler/DATA/LBC/04_ALEX_2020
CAMS=/scratch/work/lenobler/DATA/CAMS/Alex_2020
CONFIG=$TOOLBOX/CAMS/config/ALPX3.yaml
OUTPUT=/scratch/work/lenobler/DATA/LBC/09_ALEX_wt_aer
# -----------------------------------------------------------------------------

python3 $TOOLBOX/CAMS/create_LBC.py \
    --ERA5 $ERA5 \
    --CAMS $CAMS \
    --output $OUTPUT \
    --config $CONFIG
