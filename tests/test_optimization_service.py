"""
Unit tests for app/services/optimization.py

Each test works directly with the solver function — no HTTP layer involved.
The solver is non-deterministic when time-limited, so assertions target
correctness invariants rather than exact numeric values.
"""
import pytest
from app.services.optimization import run_manufacturing_optimization, ProductionConfig

ALL_SIZES = ["P", "M", "G", "GG", "G1", "G2", "G3"]
VALID_STATUSES = {"OPTIMAL", "FEASIBLE"}


# ── Helpers ──────────────────────────────────────────────────────────────────

def base_config(**overrides) -> ProductionConfig:
    cfg = ProductionConfig()
    cfg.MAX_TABLE_LENGTH_CM = 800
    cfg.FABRIC_WIDTH_CM = 180
    cfg.NESTING_EFFICIENCY = 0.85
    cfg.MAX_PATTERNS = 3
    cfg.MAX_PLY_LIMIT = 100
    cfg.SOLVER_TIME_LIMIT_SECONDS = 15.0
    for k, v in overrides.items():
        setattr(cfg, k, v)
    return cfg


def total_produced(markers: list, size: str) -> float:
    """Sum production of *size* across all markers."""
    return sum(m["layout"].get(size, 0) * m["spreading_layers"] for m in markers)


# ── Status & structure ────────────────────────────────────────────────────────

class TestSolverStatus:
    def test_returns_feasible_or_optimal(self):
        demand = {("A", "1"): {"M": 5}}
        result = run_manufacturing_optimization(demand, base_config())
        assert result["status"] in VALID_STATUSES

    def test_result_has_required_keys(self):
        demand = {("A", "1"): {"G": 3}}
        result = run_manufacturing_optimization(demand, base_config())
        assert "status" in result
        assert "financial_waste" in result
        assert "markers" in result

    def test_markers_have_required_fields(self):
        demand = {("A", "1"): {"M": 4}}
        result = run_manufacturing_optimization(demand, base_config())
        for marker in result["markers"]:
            assert "layout" in marker
            assert "layers" in marker
            assert "table_length_used_cm" in marker
            assert "utilization_pct" in marker


# ── Demand satisfaction ───────────────────────────────────────────────────────

class TestDemandSatisfaction:
    def test_single_colorway_single_size(self):
        demand = {("COLOR", "A"): {"M": 10}}
        result = run_manufacturing_optimization(demand, base_config())
        assert result["status"] in VALID_STATUSES
        assert total_produced(result["markers"], "M") >= 10

    def test_single_colorway_multi_size(self):
        demand = {("COLOR", "A"): {"P": 5, "M": 10, "G": 20, "GG": 8}}
        result = run_manufacturing_optimization(demand, base_config())
        assert result["status"] in VALID_STATUSES
        for size, qty in demand[("COLOR", "A")].items():
            assert total_produced(result["markers"], size) >= qty, (
                f"Demand not met for size {size}"
            )

    def test_multi_colorway_demand_satisfied(self):
        demand = {
            ("COLOR", "A"): {"P": 5,  "M": 10, "G": 15},
            ("COLOR", "B"): {"M": 8,  "G": 12, "GG": 6},
        }
        result = run_manufacturing_optimization(demand, base_config())
        assert result["status"] in VALID_STATUSES
        # Aggregate demand per size across colorways
        combined = {}
        for colorway_demand in demand.values():
            for size, qty in colorway_demand.items():
                combined[size] = combined.get(size, 0) + qty
        for size, qty in combined.items():
            assert total_produced(result["markers"], size) >= qty

    def test_all_sizes_in_demand(self):
        demand = {("ALL", "SZ"): {s: 3 for s in ALL_SIZES}}
        result = run_manufacturing_optimization(demand, base_config())
        assert result["status"] in VALID_STATUSES
        for size in ALL_SIZES:
            assert total_produced(result["markers"], size) >= 3


# ── Constraint enforcement ────────────────────────────────────────────────────

class TestConstraints:
    def test_max_patterns_respected(self):
        demand = {("A", "1"): {"P": 5, "M": 5, "G": 5, "GG": 5, "G1": 5}}
        result = run_manufacturing_optimization(demand, base_config(MAX_PATTERNS=2))
        assert len(result["markers"]) <= 2

    def test_single_pattern_limit(self):
        demand = {("A", "1"): {"M": 6}}
        result = run_manufacturing_optimization(demand, base_config(MAX_PATTERNS=1))
        assert len(result["markers"]) <= 1

    def test_table_length_not_exceeded(self):
        demand = {("A", "1"): {"G": 10}}
        cfg = base_config(MAX_TABLE_LENGTH_CM=800)
        result = run_manufacturing_optimization(demand, cfg)
        for marker in result["markers"]:
            assert marker["table_length_used_cm"] <= 800 + 1e-6  # float tolerance

    def test_utilization_bounded_0_to_100(self):
        demand = {("A", "1"): {"M": 5, "G": 5}}
        result = run_manufacturing_optimization(demand, base_config())
        for marker in result["markers"]:
            assert 0 <= marker["utilization_pct"] <= 100 + 1e-6

    def test_spreading_layers_positive(self):
        demand = {("A", "1"): {"M": 3}}
        result = run_manufacturing_optimization(demand, base_config())
        for marker in result["markers"]:
            assert marker["spreading_layers"] > 0

    def test_layout_contains_only_valid_sizes(self):
        demand = {("A", "1"): {"M": 4, "G": 4}}
        result = run_manufacturing_optimization(demand, base_config())
        for marker in result["markers"]:
            for size in marker["layout"]:
                assert size in ALL_SIZES


# ── Financial waste ───────────────────────────────────────────────────────────

class TestFinancialWaste:
    def test_financial_waste_non_negative(self):
        demand = {("A", "1"): {"G": 5}}
        result = run_manufacturing_optimization(demand, base_config())
        assert result["financial_waste"] >= 0

    def test_exact_fit_has_low_waste(self):
        """A single-size demand that fits cleanly should produce minimal waste."""
        demand = {("A", "1"): {"M": 10}}
        result = run_manufacturing_optimization(demand, base_config(MAX_PATTERNS=1))
        assert result["status"] in VALID_STATUSES
        # Waste in cost units — should not be absurdly high
        assert result["financial_waste"] < 1000


# ── Custom config overrides ───────────────────────────────────────────────────

class TestConfigOverrides:
    def test_custom_cost_per_size_accepted(self):
        demand = {("A", "1"): {"M": 5}}
        cfg = base_config()
        cfg.COST_PER_SIZE = {s: 1 for s in ALL_SIZES}
        result = run_manufacturing_optimization(demand, cfg)
        assert result["status"] in VALID_STATUSES

    def test_custom_area_per_size_accepted(self):
        demand = {("A", "1"): {"M": 5}}
        cfg = base_config()
        cfg.AREA_PER_SIZE_CM2 = {s: 10000 for s in ALL_SIZES}
        result = run_manufacturing_optimization(demand, cfg)
        assert result["status"] in VALID_STATUSES

    def test_high_nesting_efficiency(self):
        demand = {("A", "1"): {"G": 8}}
        result = run_manufacturing_optimization(demand, base_config(NESTING_EFFICIENCY=0.99))
        assert result["status"] in VALID_STATUSES

    def test_low_nesting_efficiency(self):
        demand = {("A", "1"): {"G": 3}}
        result = run_manufacturing_optimization(demand, base_config(NESTING_EFFICIENCY=0.60))
        assert result["status"] in VALID_STATUSES


# ── Downgrade behaviour ───────────────────────────────────────────────────────

class TestDowngrades:
    def test_downgrade_allows_demand_fulfillment(self):
        """
        If the marker produces only GG, it can downgrade to fulfill G demand.
        Total GG + G production should cover both demands.
        """
        demand = {("A", "1"): {"G": 5, "GG": 5}}
        result = run_manufacturing_optimization(demand, base_config())
        assert result["status"] in VALID_STATUSES
        # Combined production of G and GG must cover both demands (10 total)
        g_prod  = total_produced(result["markers"], "G")
        gg_prod = total_produced(result["markers"], "GG")
        assert g_prod + gg_prod >= 10
