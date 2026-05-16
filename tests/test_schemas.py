import pytest
from pydantic import ValidationError
from app.models.schemas import CutRequest, InferenceRequest

def test_cut_request_valid():
    data = {
        "demand_data": {"test": {"M": 10}},
        "table_length_cm": 800,
        "fabric_width_cm": 180
    }
    request = CutRequest(**data)
    assert request.table_length_cm == 800
    assert request.nesting_efficiency == 0.85 # Default value

def test_cut_request_invalid_dimensions():
    data = {
        "demand_data": {"test": {"M": 10}},
        "table_length_cm": 0, # Should be > 0
        "fabric_width_cm": 180
    }
    with pytest.raises(ValidationError):
        CutRequest(**data)

def test_inference_request_valid():
    data = {
        "demand_data": {"test": {"M": 10}},
        "input_markers": [{"M": 1.0}]
    }
    request = InferenceRequest(**data)
    assert len(request.input_markers) == 1
