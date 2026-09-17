using Pkg
Pkg.activate("/Users/al3792/Documents_Local/NZC_June_2026/MacroEnergy.jl")

using MacroEnergy
using Gurobi
using JuMP
using Random

case = MacroEnergy.load_case(@__DIR__)
optim = MacroEnergy.create_optimizer(Gurobi.Optimizer, nothing, ("Method" => 2, "Crossover" => 0, "BarConvTol" => 1e-3))

alg = MacroEnergy.solution_algorithm(case)
model = MacroEnergy.generate_model(case, optim, alg)

# The model already contains MGA variables for the edges selected in the case files.
least_cost = 1.39e13 # Original cost units; convert to model units below.
slack = 0.1
scaling = MacroEnergy.parameter_scaling_factor(MacroEnergy.get_settings(case))
system_cost = objective_function(model)
budget_limit = least_cost * (1 + slack) / scaling^2

# Find cost coefficients
cost_coefficients = [abs(coefficient) for (coefficient, _) in JuMP.linear_terms(system_cost)
                     if !iszero(coefficient)]
isempty(cost_coefficients) && error("The system cost has no variable coefficients.")

# Scale the entire budget row without making its smallest coefficient less than 1e-3.
budget_row_scale = max(1.0, min(least_cost / scaling^2,
                                minimum(cost_coefficients) / 1e-3))

budget = @constraint(model, system_cost / budget_row_scale <= budget_limit / budget_row_scale)

println("Parameter scale=$scaling; MGA budget row: terms=$(length(cost_coefficients)), " *
        "divisor=$budget_row_scale, " *
        "RHS=$(budget_limit / budget_row_scale), " *
        "coefficient range=[$(minimum(cost_coefficients) / budget_row_scale), " *
        "$(maximum(cost_coefficients) / budget_row_scale)]")
        
if budget_row_scale == 1.0 && first(MacroEnergy.get_periods(case)).settings.ConstraintScaling
    # Tiny cost coefficients prevent safe uniform row scaling.
    MacroEnergy.scale_constraints!(ConstraintRef[budget])
end

# Run MGA
groups = sort!(collect(keys(model[:vMGA])))
isempty(groups) && error("No MGA edges were selected in the case files.")
weights = rand(length(groups)) # One random vector, shared by the max and min solves.
mga_objective = sum(weights[i] * model[:vMGA][group] for (i, group) in enumerate(groups))

for (direction, sense) in (("max", JuMP.MOI.MAX_SENSE), ("min", JuMP.MOI.MIN_SENSE))
    set_objective_sense(model, sense)
    set_objective_function(model, mga_objective)
    optimize!(model)
    if has_values(model)
        model_cost = value(system_cost)
        println("MGA $direction: status=$(termination_status(model)), " *
                "system cost=$(model_cost * scaling^2), " *
                "budget=$(budget_limit * scaling^2)")
        model_cost <= budget_limit + max(1e-6 * budget_row_scale, 1e-9 * budget_limit) ||
            error("MGA $direction violated the cost budget.")
    end
    termination_status(model) == JuMP.MOI.OPTIMAL || error("MGA $direction failed: $(termination_status(model))")

    output_path = joinpath(@__DIR__, "MGAResults_$direction", "MGA_$(slack)_1")
    MacroEnergy.postprocess!(case, model)
    MacroEnergy.write_outputs(output_path, case, model)
    println("MGA $direction: objective=$(objective_value(model)), system cost=$(value(system_cost) * scaling^2), results=$output_path")
end
