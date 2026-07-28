using Pkg
Pkg.activate("/scratch/gpfs/JENKINS/ck0997/MacroEnergy.jl")

using MacroEnergy
using Gurobi

(case, solution) = run_case(
    @__DIR__;
    optimizer = Gurobi.Optimizer,
    optimizer_attributes = (
        "Method"       => 2,
        "BarConvTol"   => 1e-3,
        "NumericFocus" => 1,
        "Crossover"    => 0,
        "OutputFlag"   => 1,
    ),
);
