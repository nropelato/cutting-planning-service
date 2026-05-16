from ortools.sat.python import cp_model

class InferenceConfig:
    MAX_PLY_LIMIT = 100              
    SOLVER_TIME_LIMIT_SECONDS = 10.0 
    COST_PER_SIZE = {'P': 10, 'M': 12, 'G': 14, 'GG': 16, 'G1': 18, 'G2': 20, 'G3': 25}
    LAYER_TIME_PENALTY = 5           
    PATTERN_USAGE_PENALTY = 200      
    DOWNGRADE_PENALTY = 15           
    MAX_DOWNGRADE_TYPES_PER_COLOR = 2
    MAX_DOWNGRADES_PER_TYPE = 50

def optimize_predefined_markers(demand_data: dict, input_markers: list[dict], config: InferenceConfig):
    all_sizes = ['P', 'M', 'G', 'GG', 'G1', 'G2', 'G3']
    all_grouped_keys = sorted(list(demand_data.keys()))
    num_patterns = len(input_markers)

    total_demand_per_size = {size: sum(demand.get(size, 0) for demand in demand_data.values()) for size in all_sizes}
    allowed_downgrades = {'M': 'P', 'G': 'M', 'GG': 'G', 'G1': 'GG', 'G2': 'G1', 'G3': 'G2'}

    model = cp_model.CpModel()

    pattern_constants = {(p, s): int(input_markers[p].get(s, 0) * 2) for p in range(num_patterns) for s in all_sizes}

    sheets = {}
    for key in all_grouped_keys:
        total_group_demand = sum(demand_data[key].values())
        max_sheets = min(config.MAX_PLY_LIMIT, int(total_group_demand))
        for p in range(num_patterns):
            sheets[(key, p)] = model.NewIntVar(0, max_sheets, f'sheets_{key[0]}_{key[1]}_{p}')

    marker_is_used = {p: model.NewBoolVar(f'm_used_{p}') for p in range(num_patterns)}
    downgrades = {(key, p, from_s, to_s): model.NewIntVar(0, config.MAX_DOWNGRADES_PER_TYPE, f'dg_{key[0]}_{key[1]}_{p}') for key in all_grouped_keys for p in range(num_patterns) for from_s, to_s in allowed_downgrades.items()}

    for p in range(num_patterns):
        total_sheets = sum(sheets[(key, p)] for key in all_grouped_keys)
        model.Add(total_sheets > 0).OnlyEnforceIf(marker_is_used[p])
        model.Add(total_sheets == 0).OnlyEnforceIf(marker_is_used[p].Not())
        
        # Enforce structural parity constraints for half-markers
        if any(qty % 1 != 0 for qty in input_markers[p].values()):
            for key in all_grouped_keys:
                k_sheet = model.NewIntVar(0, config.MAX_PLY_LIMIT // 2, f'k_{key[0]}_{key[1]}_{p}')
                model.Add(sheets[(key, p)] == 2 * k_sheet)

    raw_prod = {(key, p, s): pattern_constants[(p, s)] * sheets[(key, p)] for key in all_grouped_keys for p in range(num_patterns) for s in all_sizes}

    for key in all_grouped_keys:
        for s in all_sizes:
            direct_production = sum(raw_prod[(key, p, s)] for p in range(num_patterns))
            gained = sum(downgrades[key, p, from_s, s] * 2 for p in range(num_patterns) for from_s, to_s in allowed_downgrades.items() if to_s == s)
            lost = sum(downgrades[key, p, s, to_s] * 2 for p in range(num_patterns) for from_s, to_s in allowed_downgrades.items() if from_s == s)
            model.Add(direct_production + gained - lost >= demand_data[key].get(s, 0) * 2)

    total_financial_waste = 0
    for s in all_sizes:
        total_prod_half = sum(raw_prod[(key, p, s)] for key in all_grouped_keys for p in range(num_patterns))
        surplus_half = total_prod_half - (total_demand_per_size[s] * 2)
        total_financial_waste += surplus_half * int(config.COST_PER_SIZE[s] / 2)

    model.Minimize(total_financial_waste + (sum(sheets.values()) * config.LAYER_TIME_PENALTY) + (sum(marker_is_used.values()) * config.PATTERN_USAGE_PENALTY))

    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    output = {"status": solver.StatusName(status), "financial_waste": 0.0, "markers": []}
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        output["financial_waste"] = float(solver.Value(total_financial_waste) / 2)
        for p in range(num_patterns):
            if solver.Value(marker_is_used[p]):
                output["markers"].append({
                    "layout": input_markers[p],
                    "layers": int(sum(solver.Value(sheets[(key, p)]) for key in all_grouped_keys))
                })
    return output
