"""
Unit tests for app/services/inference.py

Tests target the optimize_predefined_markers function directly.
Unlike solver_final, the layouts are fixed as inputs here — only
the layer count per marker per colorway is optimized.
"""
import pytest
from app.services.inference import optimize_predefined_markers, InferenceConfig

ALL_SIZES = ["P", "M", "G", "GG", "G1", "G2", "G3"]
VALID_STATUSES = {"OPTIMAL", "FEASIBLE"}


# ── Helpers ──────────────────────────────────────────────────────────────────

def base_config() -> InferenceConfig:
    cfg = InferenceConfig()
    cfg.MAX_PLY_LIMIT = 100
    cfg.SOLVER_TIME_LIMIT_SECONDS = 10.0
    return cfg


def total_produced(markers: list, size: str) -> float:
    return sum(m["layout"].get(size, 0) * m["layers"] for m in markers)


# ── Status & structure ────────────────────────────────────────────────────────

class TestInferStatus:
    def test_returns_feasible_or_optimal(self):
        result = optimize_predefined_markers(
            {("A", "1"): {"M": 5}}, [{"M": 1.0}], base_config()
        )
        assert result["status"] in VALID_STATUSES

    def test_result_has_required_keys(self):
        result = optimize_predefined_markers(
            {("A", "1"): {"G": 3}}, [{"G": 1.0}], base_config()
        )
        assert "status" in result
        assert "financial_waste" in result
        assert "markers" in result

    def test_markers_have_required_fields(self):
        result = optimize_predefined_markers(
            {("A", "1"): {"M": 4}}, [{"M": 1.0}], base_config()
        )
        for marker in result["markers"]:
            assert "layout" in marker
            assert "layers" in marker


# ── Layer count correctness ───────────────────────────────────────────────────

class TestLayerCounts:
    def test_single_marker_single_size_exact_layers(self):
        """One marker with 1 piece of M per layer must spread exactly 10 layers for 10M demand."""
        result = optimize_predefined_markers(
            {("A", "1"): {"M": 10}}, [{"M": 1.0}], base_config()
        )
        assert result["status"] in VALID_STATUSES
        assert result["markers"][0]["layers"] == 10

    def test_single_marker_multi_size_binding_constraint(self):
        """
        Marker has P=1, M=1 per layer. Demand is P=5, M=10.
        M is the binding constraint — solver must spread 10 layers,
        producing 5 surplus P pieces.
        """
        result = optimize_predefined_markers(
            {("A", "1"): {"P": 5, "M": 10}}, [{"P": 1.0, "M": 1.0}], base_config()
        )
        assert result["status"] in VALID_STATUSES
        assert result["markers"][0]["layers"] == 10

    def test_multi_marker_minimum_layers_chosen(self):
        """
        Two identical markers both covering M. Solver should use only
        the minimum layers needed rather than splitting inefficiently.
        """
        result = optimize_predefined_markers(
            {("A", "1"): {"M": 6}},
            [{"M": 1.0}, {"M": 1.0}],
            base_config(),
        )
        assert result["status"] in VALID_STATUSES
        total_layers = sum(m["layers"] for m in result["markers"])
        assert total_layers == 6

    def test_multi_colorway_layers_aggregated(self):
        """Two colorways each demanding 5M → single marker should spread 10 layers total."""
        result = optimize_predefined_markers(
            {("A", "1"): {"M": 5}, "B": {"M": 5}},
            [{"M": 1.0}],
            base_config(),
        )
        assert result["status"] in VALID_STATUSES
        assert result["markers"][0]["layers"] == 10

    def test_two_piece_marker_halves_required_layers(self):
        """Marker with M=2 per layer should need only 5 layers for 10M demand."""
        result = optimize_predefined_markers(
            {("A", "1"): {"M": 10}}, [{"M": 2.0}], base_config()
        )
        assert result["status"] in VALID_STATUSES
        assert result["markers"][0]["layers"] == 5


# ── Layout preservation ───────────────────────────────────────────────────────

class TestLayoutPreservation:
    def test_layout_identical_to_input(self):
        """The output layout must exactly match the input marker dict."""
        input_marker = {"G": 1.0, "GG": 1.0}
        result = optimize_predefined_markers(
            {("A", "1"): {"G": 3, "GG": 3}}, [input_marker], base_config()
        )
        assert result["markers"][0]["layout"] == input_marker

    def test_layout_preserved_for_multi_marker(self):
        marker_a = {"P": 1.0}
        marker_b = {"M": 1.0, "G": 1.0}
        result = optimize_predefined_markers(
            {("A", "1"): {"P": 4, "M": 3, "G": 3}},
            [marker_a, marker_b],
            base_config(),
        )
        assert result["status"] in VALID_STATUSES
        output_layouts = [m["layout"] for m in result["markers"]]
        for layout in output_layouts:
            assert layout in [marker_a, marker_b]


# ── Unused marker exclusion ───────────────────────────────────────────────────

class TestUnusedMarkers:
    def test_irrelevant_marker_excluded_from_output(self):
        """
        Demand is only for P. A marker that covers only GG should not appear
        in the output because it adds cost without fulfilling demand.
        """
        result = optimize_predefined_markers(
            {("A", "1"): {"P": 5}},
            [{"P": 1.0}, {"GG": 1.0}],
            base_config(),
        )
        assert result["status"] in VALID_STATUSES
        output_layouts = [m["layout"] for m in result["markers"]]
        assert {"GG": 1.0} not in output_layouts

    def test_all_markers_may_be_needed(self):
        """Each marker covers a disjoint size — all must be used."""
        result = optimize_predefined_markers(
            {("A", "1"): {"P": 3, "M": 3, "G": 3}},
            [{"P": 1.0}, {"M": 1.0}, {"G": 1.0}],
            base_config(),
        )
        assert result["status"] in VALID_STATUSES
        assert len(result["markers"]) == 3


# ── Half-marker parity ────────────────────────────────────────────────────────

class TestHalfMarkerParity:
    def test_half_marker_requires_even_layers(self):
        """
        A marker with fractional pieces (e.g. P=0.5) must be spread an even
        number of times so every pair of layers yields a whole garment.
        """
        result = optimize_predefined_markers(
            {("A", "1"): {"P": 6}}, [{"P": 0.5}], base_config()
        )
        assert result["status"] in VALID_STATUSES
        assert result["markers"][0]["layers"] % 2 == 0

    def test_half_marker_production_meets_demand(self):
        result = optimize_predefined_markers(
            {("A", "1"): {"P": 4, "M": 4}},
            [{"P": 0.5, "M": 0.5}],
            base_config(),
        )
        assert result["status"] in VALID_STATUSES
        assert total_produced(result["markers"], "P") >= 4
        assert total_produced(result["markers"], "M") >= 4


# ── Financial waste ───────────────────────────────────────────────────────────

class TestInferFinancialWaste:
    def test_waste_non_negative(self):
        result = optimize_predefined_markers(
            {("A", "1"): {"G": 5}}, [{"G": 1.0}], base_config()
        )
        assert result["financial_waste"] >= 0

    def test_exact_fit_zero_waste(self):
        """Single marker, single size, exact demand — no surplus expected."""
        result = optimize_predefined_markers(
            {("A", "1"): {"M": 5}}, [{"M": 1.0}], base_config()
        )
        assert result["status"] in VALID_STATUSES
        assert result["financial_waste"] == 0.0

    def test_surplus_marker_produces_waste(self):
        """
        Marker has P=1 and M=1, but demand is only P=5. Producing 5 layers
        creates 5 surplus M pieces, which should register as waste.
        """
        result = optimize_predefined_markers(
            {("A", "1"): {"P": 5}}, [{"P": 1.0, "M": 1.0}], base_config()
        )
        assert result["status"] in VALID_STATUSES
        assert result["financial_waste"] > 0


# ── Demand satisfaction invariant ────────────────────────────────────────────

class TestInferDemandSatisfaction:
    def test_all_sizes_demand_met(self):
        demand = {("A", "1"): {s: 4 for s in ["P", "M", "G", "GG"]}}
        markers = [{"P": 1.0, "M": 1.0, "G": 1.0, "GG": 1.0}]
        result = optimize_predefined_markers(demand, markers, base_config())
        assert result["status"] in VALID_STATUSES
        for size in ["P", "M", "G", "GG"]:
            assert total_produced(result["markers"], size) >= 4

    def test_multi_colorway_each_satisfied(self):
        demand = {("A", "1"): {"G": 3}, "B": {"G": 4}, "C": {"G": 2}}
        result = optimize_predefined_markers(demand, [{"G": 1.0}], base_config())
        assert result["status"] in VALID_STATUSES
        assert total_produced(result["markers"], "G") >= 9
