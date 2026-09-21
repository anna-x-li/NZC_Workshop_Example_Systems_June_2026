using Pkg
Pkg.activate("/home/al3792/NZC_MGA/MacroEnergy.jl")
using MacroEnergy, Gurobi
const J = MacroEnergy.JuMP
case = MacroEnergy.load_case(joinpath(@__DIR__, "inputs"))
case = MacroEnergy.Case(case.systems, merge(case.settings, (MGA = merge(case.settings.MGA, (Enabled=true, Epsilon=0.05, RandomSeed=2, MGAAlgorithm="RandomVector", NumIterations=1)),)))
optim = MacroEnergy.create_optimizer(Gurobi.Optimizer, nothing, ("Method"=>2, "Crossover"=>0, "BarConvTol"=>1e-6))
model = MacroEnergy.generate_model(case, optim, MacroEnergy.solution_algorithm(case))
cost = J.objective_function(model)
parameter_scale = MacroEnergy.parameter_scaling_factor(MacroEnergy.get_settings(case))
least_cost = 1.39e13 / parameter_scale^2
min_coefficient = minimum(abs(c) for (c, _) in J.linear_terms(cost) if !iszero(c))
budget_divisor = max(1.0, min(least_cost, min_coefficient / 1e-3))
open(joinpath(@__DIR__, "mga_budget_coefficients.txt"), "w") do io
    MacroEnergy.report_mga_budget_coefficients(io, cost; divisor=budget_divisor,
        budget_limit=1.05 * least_cost, top_n=30)
end
open(joinpath(@__DIR__, "variable_names.tsv"), "w") do io
    println(io, "index\tname\tlower_bound\tupper_bound")
    for line in eachline(joinpath(@__DIR__, "indices.txt"))
        i = parse(Int, line)
        v = J.VariableRef(model, J.MOI.VariableIndex(i))
        if J.is_valid(model, v)
            println(io, i, '\t', J.name(v), '\t', J.has_lower_bound(v) ? J.lower_bound(v) : "none", '\t', J.has_upper_bound(v) ? J.upper_bound(v) : "none")
        else
            println(io, i, "\tINVALID")
        end
    end
end
println("LOOKUP COMPLETE: ", J.num_variables(model), " variables; no optimization performed")
