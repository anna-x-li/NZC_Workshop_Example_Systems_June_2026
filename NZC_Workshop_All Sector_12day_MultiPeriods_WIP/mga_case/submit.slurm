#!/bin/bash
#SBATCH --job-name=nzc-4stage
#SBATCH --account=jenkins
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=45G
#SBATCH --time=01:30:00
#SBATCH --output=slurm-%j.out
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=ck0997@princeton.edu

module purge
module load gurobi/13.0.0

julia --threads=$SLURM_CPUS_PER_TASK run.jl
