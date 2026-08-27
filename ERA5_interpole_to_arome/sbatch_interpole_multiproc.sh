#!/bin/bash
#SBATCH --job-name=era5_interp
#SBATCH --nodes=1
#SBATCH --time=02:10:00
#SBATCH --cpus-per-task=32

source ~/SAVE/code/GL/config/setenv.belenos
module load gcc/14.1.0

export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1

NNODES=$SLURM_JOB_NUM_NODES

INPUT=/scratch/work/lenobler/DATA/LBC/00_ERA5/ALEX_2020
OUTPUT=/scratch/work/lenobler/DATA/LBC/04_ALEX_2020

. with_epygram_old
python3 /home/gmgec/mrgo/lenobler/SAVE/scripts/MARS/interpole_current_folder_multiproc.py \
                                    --input_folder $INPUT \
                                    --output_folder $OUTPUT \
                                    --nproc $SLURM_CPUS_PER_TASK
