#!/bin/bash
#SBATCH --job-name=mga_name_lookup
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=150G
#SBATCH --time=01:00:00
set -euo pipefail
module purge
module load gurobi/13.0.0
module load julia/1.12.1
export OMP_NUM_THREADS=4

exec julia --threads=4 lookup.jl
