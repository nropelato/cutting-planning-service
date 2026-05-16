from ortools.sat.python import cp_model
from app.core.config import settings

class ProductionConfig:
    """
    Industrial parameters for the cutting room.
    """
    MAX_PATTERNS = 3                 
    MAX_PLY_LIMIT = 100              
    SOLVER_TIME_LIMIT_SECONDS = 30.0 
    MAX_TABLE_LENGTH_CM = 800        
    FABRIC_WIDTH_CM = 180            
    NESTING_EFFICIENCY = 0.85        
    
    # Area in cm2 for a FULL garment
    AREA_PER_SIZE_CM2 = {
        'P': 12000, 'M': 13500, 'G': 15000, 'GG': 16500, 'G1': 18000, 'G2': 19500, 'G3': 21000
    }
    
    # Financial cost per FULL garment
    COST_PER_SIZE = {
        'P': 10, 'M': 12, 'G': 14, 'GG': 16, 'G1': 18, 'G2': 20, 'G3': 25
    }

    # Financial Operation Costs (from settings/env)
    LAYER_SPREADING_COST = settings.LAYER_SPREADING_COST
    MARKER_FIXED_BASE_COST = settings.MARKER_FIXED_BASE_COST
    MARKER_PAPER_COST_PER_CM = settings.MARKER_PAPER_COST_PER_CM
    SUBSTITUTION_ANNOYANCE_TAX = settings.SUBSTITUTION_ANNOYANCE_TAX
    
    # Short-Shipping Tolerance Gates
    MAX_SHORTAGE_PCT = settings.MAX_SHORTAGE_PCT
    SHORTAGE_PENALTY_MULTIPLIER = settings.SHORTAGE_PENALTY_MULTIPLIER

    MAX_DOWNGRADE_TYPES_PER_COLOR = 2
    MAX_DOWNGRADES_PER_TYPE = 50

def run_manufacturing_optimization(demand_data: dict, config: ProductionConfig, anomaly_pct: float, anomaly_ceil: int):
    """
    Financial-Industrial Solver 2.0 (Refined TCO)
    Minimizes Total Cost of Operation (TCO) with strategic underproduction slack.
    """
    all_sizes = ['P', 'M', 'G', 'GG', 'G1', 'G2', 'G3']
    all_grouped_keys = sorted(list(demand_data.keys()))

    # Calculate total demand
    total_demand_per_size = {
        size: sum(demand.get(size, 0) for demand in demand_data.values())
        for size in all_sizes
    }
    
    allowed_downgrades = {
        'M': 'P', 'G': 'M', 'GG': 'G', 'G1': 'GG', 'G2': 'G1', 'G3': 'G2'
    }

    model = cp_model.CpModel()
    
    # Area Ceiling: Hard physical boundary of the table (Width * Length * Efficiency)
    max_usable_area_half = int((config.MAX_TABLE_LENGTH_CM * config.FABRIC_WIDTH_CM * config.NESTING_EFFICIENCY))

    # 1. Variables
    patterns = {}
    for p in range(config.MAX_PATTERNS):
        for s in all_sizes:
            # 1 template = 0.5 garments
            max_templates = int((max_usable_area_half * 2) / config.AREA_PER_SIZE_CM2[s])
            patterns[(p, s)] = model.NewIntVar(0, max_templates, f'pattern_{p}_{s}')

    sheets = {}
    for key in all_grouped_keys:
        total_group_demand = sum(demand_data[key].values())
        max_sheets = min(config.MAX_PLY_LIMIT, int(total_group_demand))
        for p in range(config.MAX_PATTERNS):
            safe_key = str(key).replace(" ", "_").replace("/", "_").replace("(", "").replace(")", "")
            sheets[(key, p)] = model.NewIntVar(0, max_sheets, f'sheets_{safe_key}_{p}')

    downgrades_vars = {}
    for key in all_grouped_keys:
        safe_key = str(key).replace(" ", "_").replace("/", "_").replace("(", "").replace(")", "")
        for p in range(config.MAX_PATTERNS):
            for from_s, to_s in allowed_downgrades.items():
                downgrades_vars[(key, p, from_s, to_s)] = model.NewIntVar(
                    0, config.MAX_DOWNGRADES_PER_TYPE, f'dg_{safe_key}_{p}_{from_s}_{to_s}'
                )

    # Define a shortage tracking variable for every size and colorway (Slack Variables)
    shortage_vars = {}
    for key in all_grouped_keys:
        safe_key = str(key).replace(" ", "_").replace("/", "_").replace("(", "").replace(")", "")
        
        # 1. Identify the Anchor Size (Highest demand in this specific colorway batch)
        highest_size_demand = max(demand_data[key].values()) if demand_data[key] else 0
        
        # 2. Compute the dynamic anomaly gate
        calculated_gate = int(highest_size_demand * anomaly_pct)
        
        # 3. Apply the hard protection backstop
        current_anomaly_threshold = min(anomaly_ceil, calculated_gate)
        current_anomaly_threshold = max(1, current_anomaly_threshold) 

        for s in all_sizes:
            raw_size_demand = demand_data[key].get(s, 0)
            
            if raw_size_demand <= current_anomaly_threshold:
                # Awkward anomaly; can be shorted up to 100%
                max_size_short_pieces = raw_size_demand
            else:
                # Standard operational backstop (12% tolerance)
                max_size_short_pieces = int(raw_size_demand * 0.12)
                
            shortage_vars[(key, s)] = model.NewIntVar(0, max_size_short_pieces, f'shortage_{safe_key}_{s}')

    pattern_is_used = {p: model.NewBoolVar(f'p_used_{p}') for p in range(config.MAX_PATTERNS)}

    # 2. Constraints
    for p in range(config.MAX_PATTERNS):
        total_area_used_half = sum(patterns[(p, s)] * (config.AREA_PER_SIZE_CM2[s] // 2) for s in all_sizes)
        model.Add(total_area_used_half <= max_usable_area_half)
        model.Add(total_area_used_half > 0).OnlyEnforceIf(pattern_is_used[p])
        model.Add(total_area_used_half == 0).OnlyEnforceIf(pattern_is_used[p].Not())

    raw_prod = {}
    for key in all_grouped_keys:
        safe_key = str(key).replace(" ", "_").replace("/", "_").replace("(", "").replace(")", "")
        for p in range(config.MAX_PATTERNS):
            for s in all_sizes:
                max_templates = int((max_usable_area_half * 2) / config.AREA_PER_SIZE_CM2[s])
                max_yield = max_templates * config.MAX_PLY_LIMIT
                raw_prod[(key, p, s)] = model.NewIntVar(0, max_yield, f'raw_{safe_key}_{p}_{s}')
                model.AddMultiplicationEquality(raw_prod[(key, p, s)], patterns[(p, s)], sheets[(key, p)])

    # 3. Demand Fulfillment with Slack
    surplus_vars = {}
    for key in all_grouped_keys:
        safe_key = str(key).replace(" ", "_").replace("/", "_").replace("(", "").replace(")", "")
        for s in all_sizes:
            direct_production = sum(raw_prod[(key, p, s)] for p in range(config.MAX_PATTERNS))
            gained = sum(downgrades_vars[key, p, from_s, s] * 2 for p in range(config.MAX_PATTERNS) for from_s, to_s in allowed_downgrades.items() if to_s == s)
            lost = sum(downgrades_vars[key, p, s, to_s] * 2 for p in range(config.MAX_PATTERNS) for from_s, to_s in allowed_downgrades.items() if from_s == s)
            
            # Surplus Variable to handle overproduction waste
            surplus_vars[(key, s)] = model.NewIntVar(0, 1000, f'surplus_{safe_key}_{s}')
            
            # Equation: Production + Gained - Lost + (Shortage * 2) - Surplus == Demand * 2
            model.Add(direct_production + gained - lost + (shortage_vars[(key, s)] * 2) - surplus_vars[(key, s)] == demand_data[key].get(s, 0) * 2)

    for p in range(config.MAX_PATTERNS - 1):
        model.Add(sum(patterns[(p, s)] for s in all_sizes) >= sum(patterns[(p + 1, s)] for s in all_sizes))

    # --- 4. MINIMIZATION FUNCTION ---
    # A. Material Waste Component
    total_financial_waste_scaled = sum(surplus_vars[(key, s)] * int(config.COST_PER_SIZE[s] * 100 / 2) for key in all_grouped_keys for s in all_sizes)

    # B. Setup Component
    total_marker_setup_cost_scaled = 0
    max_usable_width_flow = config.FABRIC_WIDTH_CM * config.NESTING_EFFICIENCY
    for p in range(config.MAX_PATTERNS):
        length_weight_per_half_piece = {s: int((config.AREA_PER_SIZE_CM2[s] / 2) / max_usable_width_flow) for s in all_sizes}
        marker_length_cm = sum(patterns[(p, s)] * length_weight_per_half_piece[s] for s in all_sizes)
        total_marker_setup_cost_scaled += (pattern_is_used[p] * int(config.MARKER_FIXED_BASE_COST * 100)) + \
                                          (marker_length_cm * int(config.MARKER_PAPER_COST_PER_CM * 100))

    # C. Labor and Downgrades
    total_sheets = sum(sheets[key, p] for key in all_grouped_keys for p in range(config.MAX_PATTERNS))
    total_labor_cost_scaled = total_sheets * int(config.LAYER_SPREADING_COST * 100)

    total_downgrades_sum_scaled = 0
    for (key, p, from_s, to_s), var in downgrades_vars.items():
        material_loss = config.COST_PER_SIZE[from_s] - config.COST_PER_SIZE[to_s]
        unit_penalty = material_loss + config.SUBSTITUTION_ANNOYANCE_TAX
        total_downgrades_sum_scaled += var * int(unit_penalty * 100)

    # D. Shortage Component
    total_shortage_penalty_scaled = 0
    for key in all_grouped_keys:
        for s in all_sizes:
            unit_shortage_fee = int(config.COST_PER_SIZE[s] * config.SHORTAGE_PENALTY_MULTIPLIER * 100)
            total_shortage_penalty_scaled += shortage_vars[(key, s)] * unit_shortage_fee

    model.Minimize(total_financial_waste_scaled + total_marker_setup_cost_scaled + total_shortage_penalty_scaled + total_labor_cost_scaled + total_downgrades_sum_scaled)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = config.SOLVER_TIME_LIMIT_SECONDS
    solver.parameters.relative_gap_limit = 0.01
    status = solver.Solve(model)

    output = {"status": solver.StatusName(status), "total_cost": 0.0, "total_financial_waste": 0.0, "labor_cost": 0.0, "setup_cost": 0.0, "downgrade_cost": 0.0, "shortage_cost": 0.0, "markers": [], "ledger": []}
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        output["total_cost"] = float(solver.ObjectiveValue() / 100)
        output["total_financial_waste"] = float(solver.Value(total_financial_waste_scaled) / 100)
        output["labor_cost"] = float(solver.Value(total_labor_cost_scaled) / 100)
        output["setup_cost"] = float(solver.Value(total_marker_setup_cost_scaled) / 100)
        output["downgrade_cost"] = float(solver.Value(total_downgrades_sum_scaled) / 100)
        output["shortage_cost"] = float(solver.Value(total_shortage_penalty_scaled) / 100)
        
        for key in all_grouped_keys:
            for s in all_sizes:
                prod_half = sum(solver.Value(raw_prod[(key, p, s)]) for p in range(config.MAX_PATTERNS))
                short_qty = solver.Value(shortage_vars[(key, s)])
                if prod_half > 0 or short_qty > 0:
                    output["ledger"].append({"key": str(key), "size": s, "production_qty": int(prod_half / 2), "shortage_qty": int(short_qty)})

        for p in range(config.MAX_PATTERNS):
            if solver.Value(pattern_is_used[p]):
                area_used_half = sum(solver.Value(patterns[(p, s)]) * (config.AREA_PER_SIZE_CM2[s] // 2) for s in all_sizes)
                output["markers"].append({
                    "layout": {s: solver.Value(patterns[(p, s)]) for s in all_sizes if solver.Value(patterns[(p, s)]) > 0},
                    "layers": int(sum(solver.Value(sheets[(key, p)]) for key in all_grouped_keys)),
                    "table_length_used_cm": float(area_used_half / max_usable_width_flow),
                    "utilization_pct": float((area_used_half / max_usable_area_half) * 100)
                })
    return output
