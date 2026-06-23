using MacroEnergy
using Gurobi
using Logging

(system, model) = run_case(
    @__DIR__;
    log_level=Logging.Debug,
    optimizer = Gurobi.Optimizer,
    lazy_load = false,
    optimizer_attributes = (
        "Method"       => 2,
        "Threads"      => 8,
        "BarConvTol"   => 1e-4,
        "NumericFocus" => 1,
	    "Crossover"    => 0,
        "OutputFlag"   => 1,
        "LogFile"      => joinpath(@__DIR__, "gurobi.log")
    ),
);