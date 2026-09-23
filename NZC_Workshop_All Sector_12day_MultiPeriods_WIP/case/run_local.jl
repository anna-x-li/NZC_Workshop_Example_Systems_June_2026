using Pkg
Pkg.activate("/Users/al3792/Documents_Local/NZC_June_2026/MacroEnergy.jl")

using MacroEnergy
using Gurobi
using Random
using Dates

#### Just run a least cost solution

(system, model) = run_case(@__DIR__; 
                    optimizer=Gurobi.Optimizer,
                    optimizer_attributes=("Method" => 2, "Crossover" => 0, "BarConvTol" => 1e-6));

#### Just run MGA with

case = MacroEnergy.load_case(@__DIR__)

optim = MacroEnergy.create_optimizer(Gurobi.Optimizer, nothing,
    ("Method" => 2, "Crossover" => 0, "BarConvTol" => 1e-6,
     "LogFile" => joinpath(@__DIR__, "mga_gurobi.log"),
    ))

alg = MacroEnergy.solution_algorithm(case)

#log_progress("Starting model generation")

model = MacroEnergy.generate_model(case, optim, alg)

#log_progress("Model generated; starting MGA")

# The batch seed overrides the JSON seed above; standalone runs use the JSON value.
seed = case.settings.MGA.RandomSeed
isnothing(seed) || Random.seed!(seed)
rng = Random.default_rng()
MacroEnergy.run_mga(case, model, @__DIR__; rng=rng, least_cost_original=1.37413e13)