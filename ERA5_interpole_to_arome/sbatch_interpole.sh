#!/bin/bash
#SBATCH --job-name=era5_interp
#SBATCH --nodes=1
#SBATCH --time=00:10:00

source ~/SAVE/code/GL/config/setenv.belenos
module load gcc/14.1.0

NNODES=$SLURM_JOB_NUM_NODES

INPUT=/scratch/work/lenobler/DATA/LBC/00_ERA5/ALEX_2020/
OUTPUT=/scratch/work/lenobler/DATA/ERA5/05_test

. with_epygram_old
MPITASKS_PER_NODE=$((NNODES*16)) 

srun -N $NNODES -n $MPITASKS_PER_NODE python3 /home/gmgec/mrgo/lenobler/SAVE/scripts/MARS/interpole_current_folder_mpi.py \
                                    --input_folder $INPUT \
                                    --output_folder $OUTPUT
