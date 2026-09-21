#!/bin/bash
set -euo pipefail

# Find the case containing this script.
case_dir="$(cd -- "$(dirname -- "$0")" && pwd)"

# Store logs, private inputs, and results together on scratch.
results_root="/scratch/gpfs/JENKINS/al3792/NZC_MGA/12day_MultiPeriods/results"
mkdir -p "$results_root"
# Explicit timezone; nanoseconds avoid collisions between simultaneous launches.
sweep_dir="$results_root/MGA_sweep_$(TZ=America/New_York date +%Y-%m-%d_%H-%M-%S-%N_%Z)"
mkdir "$sweep_dir"
echo "Saving this sweep to: $sweep_dir"

# Edit the slack values and seed range below.
# Each seed is reused at every slack for comparable random objectives.
for seed in {1..20}; do
    for slack in 0.01 0.05 0.10; do
        output_dir="$sweep_dir/slack_$slack/seed_$seed"
        mkdir -p "$output_dir"

        echo "Submitting slack=$slack, seed=$seed"
        sbatch --parsable \
            --job-name="mga_${slack}_${seed}" \
            --chdir="$output_dir" \
            --output="$output_dir/slurm-%j.out" \
            --error="$output_dir/slurm-%j.err" \
            "$case_dir/mga_job.slurm" \
            "$case_dir/run.jl" "$slack" "$seed" "$output_dir" \
            > "$output_dir/job_id.txt"
        echo "Submitted job $(cat "$output_dir/job_id.txt")"
    done
done
