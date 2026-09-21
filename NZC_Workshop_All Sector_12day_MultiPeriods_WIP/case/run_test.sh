#!/bin/bash

#SBATCH --job-name=mga_one_stage_test_2
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=150G
#SBATCH --time=04:00:00
#SBATCH --output=slurm-%j.out
#SBATCH --mail-type=all                       # send email when job ends
#SBATCH --mail-user=al3792@princeton.edu

module purge
module load gurobi/13.0.0

module load julia/1.12.1
julia run_test.jl