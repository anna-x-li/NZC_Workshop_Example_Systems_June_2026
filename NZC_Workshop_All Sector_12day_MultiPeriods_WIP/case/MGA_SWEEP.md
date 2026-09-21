Run this from the case directory to submit the sweep:

```bash
bash submit_mga_sweep.sh
```

The two loops in `submit_mga_sweep.sh` control the experiment:

```bash
for seed in {1..20}; do
    for slack in 0.01 0.05 0.10; do
        # Submit run.jl with this slack and seed.
    done
done
```

Edit those values directly. For example, `{21..40}` uses seeds 21 through 40.
The defaults submit 60 jobs, each solving one max/min pair (120 solves total).
The same seed is reused across slacks to generate matching random objectives.

Each submission calls `mga_job.slurm`, which copies the driver and case inputs
into a private `case_inputs_<unique>` directory inside the job's output folder.
This prevents MacroEnergy's input-loading code from rewriting a JSON file while
another job reads it. The copy is retained for inspection (about 32 MB per job).
The script loads Julia and Gurobi, sets `OMP_NUM_THREADS` to the allocated CPU
count, and runs the copied driver:

```bash
julia --threads="$SLURM_CPUS_PER_TASK" "$run_file" "$slack" "$seed" "$output_dir"
```

`run.jl` applies the slack and seed in memory and builds a fresh model. It does
not edit the shared JSON settings. For a standalone `julia run.jl`, set
`MGA.RandomSeed` in `settings/case_settings.json` instead (`null` means unseeded).
The existing `least_cost_original=1.39e13` baseline is retained.

Every sweep gets a new folder to avoid overwriting previous runs:

```text
results/MGA_sweep_<unique>/
  slack_0.01/seed_1/
    job_id.txt
    slurm-<job_id>.out
    slurm-<job_id>.err
    mga_run_settings.txt
    results/MGAResults_max_01/MGA_0.01_1/
      numerical_diagnostics.txt
      mga_summary.csv
      ...
    results/MGAResults_min_01/MGA_0.01_1/
      ...
```

Edit resource requests in `mga_job.slurm`: defaults are 4 CPUs, 150 GB, and
6 hours, using Gurobi 13.0.0 and Julia 1.12.1. If a submission fails, the script
stops; already submitted jobs keep running and their IDs remain in `job_id.txt`.

Extra progress and Gurobi file logging in `run.jl` is commented out. Solver
console output stays in the Slurm log; numerical diagnostics remain in the MGA folders.
