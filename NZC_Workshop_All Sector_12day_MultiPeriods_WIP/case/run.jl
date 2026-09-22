using Pkg
Pkg.activate("/home/al3792/NZC_MGA/MacroEnergy.jl")

# Batch jobs pass epsilon, seed, and an isolated output directory.
length(ARGS) in (0, 3) || error("Usage: run.jl [epsilon seed output_directory]")
if isempty(ARGS)
    results_root = "/scratch/gpfs/JENKINS/al3792/NZC_MGA/12day_MultiPeriods/results"
    mkpath(results_root)
    output_path = joinpath(results_root, "MGA_run_" * Dates.format(Dates.now(Dates.UTC), "yyyy-mm-dd_HH-MM-SS-sss") * "_UTC")
    mkdir(output_path) # Refuse to overwrite an existing standalone run.
else
    output_path = abspath(ARGS[3])
    mkpath(output_path)
end
# progress_log = joinpath(output_path, "mga_progress.log")
# function log_progress(message)
#     open(progress_log, "a") do io
#         println(io, "$(Dates.now()) $message")
#     end
# end

# log_progress("Starting case load")

case = MacroEnergy.load_case(@__DIR__)
if !isempty(ARGS)
    epsilon = parse(Float64, ARGS[1])
    seed = parse(Int, ARGS[2])  # Seed passed by submit_mga_sweep.sh through mga_job.slurm.
    isfinite(epsilon) && epsilon >= 0 || error("epsilon must be finite and nonnegative")
    seed >= 0 || error("seed must be nonnegative")
    mga = merge(case.settings.MGA, (
        Enabled = true, Epsilon = epsilon, RandomSeed = seed,
        MGAAlgorithm = "RandomVector", NumIterations = 1,
    ))
    case = MacroEnergy.Case(case.systems, merge(case.settings, (MGA = mga,)))
end
open(joinpath(output_path, "mga_run_settings.txt"), "w") do io
    println(io, "MGA = ", case.settings.MGA)
    println(io, "least_cost_original = 1.39e13")
end
# log_progress("Case loaded; creating optimizer")
optim = MacroEnergy.create_optimizer(Gurobi.Optimizer, nothing,
    ("Method" => 2, "Crossover" => 0, "BarConvTol" => 1e-6,
     # "LogFile" => joinpath(output_path, "mga_gurobi.log"),
    ))

alg = MacroEnergy.solution_algorithm(case)
# log_progress("Starting model generation")
model = MacroEnergy.generate_model(case, optim, alg)
# log_progress("Model generated; starting MGA")

# The batch seed overrides the JSON seed above; standalone runs use the JSON value.
seed = case.settings.MGA.RandomSeed
rng = isnothing(seed) ? Random.default_rng() : MersenneTwister(seed)
MacroEnergy.run_mga(case, model, output_path; rng=rng, least_cost_original=1.39e13)
# log_progress("MGA finished")

# MacroEnergy.optimize!(model)

# Compute conflicts

# MacroEnergy.compute_conflict!(model)
# list_of_conflicting_constraints = MacroEnergy.ConstraintRef[];
# for (F, S) in MacroEnergy.list_of_constraint_types(model)
#     for con in MacroEnergy.JuMP.all_constraints(model, F, S)
#         if MacroEnergy.JuMP.get_attribute(con, MacroEnergy.MOI.ConstraintConflictStatus()) == MacroEnergy.MOI.IN_CONFLICT
#             push!(list_of_conflicting_constraints, con)
#         end
#     end
# end
# display(list_of_conflicting_constraints)

# # Save the list of conflicting constraints to a text file
# function clean_constraint_list(input_list::Vector{JuMP.ConstraintRef})
#     seen_patterns = Set{String}()
#     cleaned_list = String[] # We return strings for the text file

#     for constraint in input_list
#         line = string(constraint)
#         normalized = replace(line, r"\[\d+\]" => "[]")
#         if !(normalized in seen_patterns)
#             push!(seen_patterns, normalized)
#             push!(cleaned_list, line)
#         end
#     end

#     return cleaned_list
# end

# result = clean_constraint_list(list_of_conflicting_constraints)

# open("conflicting_constraints.txt", "w") do io
#     for item in result
#         println(io, item)
#     end
# end

# # Restore original system_data.json
# write(system_data_path, original_system_data)

# case = MacroEnergy.load_case(@__DIR__)

# (case, solution) = run_case(
#     @__DIR__;
#     optimizer=Gurobi.Optimizer,
#     lazy_load=false,
#     optimizer_attributes=(
#         "Method" => 2,
#         "Threads" => -1,
#         "BarConvTol" => 1e-3,
#         "NumericFocus" => 1,
#         "Crossover" => 0,
#         "OutputFlag" => 1,
#     ),
# );
