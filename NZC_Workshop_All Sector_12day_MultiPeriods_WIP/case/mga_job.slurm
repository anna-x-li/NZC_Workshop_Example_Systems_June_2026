#!/bin/bash
#SBATCH --job-name=mga_one_stage_2
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=150G
#SBATCH --time=6:00:00
#SBATCH --output=slurm-%j.out
#SBATCH --mail-type=all                       # send email when job ends
#SBATCH --mail-user=al3792@princeton.edu

set -euo pipefail

# Arguments: absolute run.jl path, epsilon, seed, absolute output directory.
[[ $# -eq 4 ]] || { echo "Expected: run.jl epsilon seed output_directory" >&2; exit 2; }
run_file="$1"
slack="$2"
seed="$3"
output_dir="$4"

# MacroEnergy rewrites system_data.json during loading. Copy the driver and
# inputs so run.jl's @__DIR__ points at a private case for this job.
case_dir="$(cd -- "$(dirname -- "$run_file")" && pwd)"
mkdir -p "$output_dir"
output_dir="$(cd -- "$output_dir" && pwd)"
job_case_dir="$(mktemp -d "$output_dir/case_inputs_XXXXXX")"
cp -RL -- "$run_file" "$job_case_dir/run.jl"
for input in system_data.json assets system settings tools user_additions; do
    cp -RL -- "$case_dir/$input" "$job_case_dir/$input"
done
run_file="$job_case_dir/run.jl"
cd -- "$output_dir"
echo "Private case inputs: $job_case_dir"

module purge
module load gurobi/13.0.0
module load julia/1.12.1

# Override invalid inherited OpenMP settings after loading the modules.
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-4}"

exec julia --threads="${SLURM_CPUS_PER_TASK:-4}" "$run_file" "$slack" "$seed" "$output_dir"
