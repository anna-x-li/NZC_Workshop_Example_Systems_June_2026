# Run from any directory:
#   julia run_one_stage_no_co2_cap.jl
# Validate the input overrides without building/solving:
#   julia run_one_stage_no_co2_cap.jl --check-inputs
# Original JSON files are never modified. MGA is disabled for this least-cost run.
using Pkg
const CASE_DIR = @__DIR__
const MACRO_PROJECT = get(ENV, "MACROENERGY_PROJECT",
    normpath(joinpath(CASE_DIR, "..", "..", "..", "MacroEnergy.jl")))
Pkg.activate(MACRO_PROJECT)

using MacroEnergy
using Gurobi
using JuMP
using Dates

function disable_co2_caps!(data)
    count = 0
    if data isa AbstractDict
        if haskey(data, :constraints) && haskey(data[:constraints], :CO2CapConstraint)
            count += data[:constraints][:CO2CapConstraint] === true
            data[:constraints][:CO2CapConstraint] = false
        end
        # Remove cap budgets and violation penalties as well as disabling the constraint.
        for key in (:rhs_policy, :price_unmet_policy)
            if haskey(data, key)
                pop!(data[key], :CO2CapConstraint, nothing)
            end
        end
        for value in values(data)
            count += disable_co2_caps!(value)
        end
    elseif data isa AbstractVector
        for value in data
            count += disable_co2_caps!(value)
        end
    end
    return count
end

function first_stage_inputs()
    manifest = joinpath(CASE_DIR, "system_data.json")
    data = MacroEnergy.load_case_data(manifest)
    data[:case] = data[:case][1:1]
    stage = only(data[:case])
    settings = MacroEnergy.load_inputs(joinpath(CASE_DIR, data[:settings][:path]);
                                      rel_path=CASE_DIR, lazy_load=false)
    settings[:PeriodLengths] = settings[:PeriodLengths][1:1] # Retain original 5-year duration.
    settings[:SolutionAlgorithm] = "Monolithic"
    settings[:ExpansionHorizon] = "PerfectForesight"
    settings[:MGA] = merge(get(settings, :MGA, Dict{Symbol,Any}()), Dict(:Enabled => false))
    data[:settings] = settings

    nodes = MacroEnergy.load_inputs(joinpath(CASE_DIR, stage[:nodes][:path]);
                                   rel_path=CASE_DIR, lazy_load=false)
    disabled = disable_co2_caps!(nodes)
    # The first stage may already have its CO2 cap disabled in the source inputs.
    stage[:nodes] = nodes
    system_settings = MacroEnergy.load_inputs(joinpath(CASE_DIR, stage[:settings][:path]);
                                              rel_path=CASE_DIR, lazy_load=false)
    system_settings[:OutputDir] = "results_one_stage_no_co2_cap"
    stage[:settings] = system_settings
    @info "Prepared first stage without CO2 caps" period_lengths=settings[:PeriodLengths] disabled_caps=disabled
    return manifest, data
end

function solve_first_stage(manifest, data)
    case = MacroEnergy.generate_case(manifest, data)
    @assert length(case.systems) == 1
    @assert all(!any(c -> c isa MacroEnergy.CO2CapConstraint, n.constraints)
                for n in only(case.systems).locations if n isa MacroEnergy.Node)
    # A unique run folder preserves earlier results, including earlier uncapped runs.
    output_dir = mktempdir(mkpath(joinpath(CASE_DIR, "results_one_stage_no_co2_cap"));
                          prefix=Dates.format(now(), "yyyymmdd_HHMMSS") * "_", cleanup=false)
    optimizer = MacroEnergy.create_optimizer(Gurobi.Optimizer, nothing,
        ("Method" => 2, "Crossover" => 0, "BarConvTol" => 1e-6,
         "LogFile" => joinpath(output_dir, "gurobi.log")))
    try
        case, model = MacroEnergy.solve_case(case, optimizer)
        is_solved_and_feasible(model) || error("Optimization failed: $(termination_status(model))")
        MacroEnergy.postprocess!(case, model)
        MacroEnergy.write_outputs(output_dir, case, model)
        @info "First-stage optimization complete" output_dir
        return case, model
    finally
        MacroEnergy.unscale!(case, MacroEnergy.parameter_scaling_factor(case.settings))
    end
end

function main()
    manifest, data = first_stage_inputs()
    "--check-inputs" in ARGS && return nothing
    try
        MacroEnergy.setup_user_additions(CASE_DIR)
        MacroEnergy.load_user_additions(CASE_DIR)
        MacroEnergy.refresh_user_type_registries!()
        return Base.invokelatest(solve_first_stage, manifest, data)
    finally
        MacroEnergy.case_cleanup()
    end
end

main()
