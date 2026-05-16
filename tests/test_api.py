from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)
AUTH_HEADERS = {"X-API-KEY": settings.API_KEY}

def test_health_check():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "healthy", "engine": "OR-Tools CP-SAT"}

def test_security_auth_locks():
    # Missing header -> 403 (FastAPI's APIKeyHeader behavior)
    assert client.post("/api/v1/optimize", json={}).status_code == 403
    # Bad header -> 401 (Our verification logic)
    assert client.post("/api/v1/optimize", headers={"X-API-KEY": "bad"}, json={}).status_code == 401

def test_dynamic_generation_endpoint_success():
    payload = {
        "demand_data": {"2020/186": {'P': 5, 'M': 5, 'G': 26, 'GG': 18}},
        "table_length_cm": 800, 
        "fabric_width_cm": 180, 
        "nesting_efficiency": 0.85
    }
    res = client.post("/api/v1/optimize", headers=AUTH_HEADERS, json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "markers" in data
    assert len(data["markers"]) > 0

def test_dynamic_generation_validation_error():
    # Missing required field 'table_length_cm'
    payload = {
        "demand_data": {"2020/186": {'P': 5}},
        "fabric_width_cm": 180
    }
    res = client.post("/api/v1/optimize", headers=AUTH_HEADERS, json=payload)
    assert res.status_code == 422

def test_inference_layer_endpoint_success():
    payload = {
        "demand_data": {"2020/186": {'P': 10, 'M': 10}},
        "input_markers": [{"P": 1.0, "M": 1.0}]
    }
    res = client.post("/api/v1/infer-layers", headers=AUTH_HEADERS, json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["markers"][0]["spreading_layers"] == 10

def test_inference_layer_validation_error():
    # input_markers should be a list, not a dict
    payload = {
        "demand_data": {"2020/186": {'P': 10}},
        "input_markers": {"P": 1.0}
    }
    res = client.post("/api/v1/infer-layers", headers=AUTH_HEADERS, json=payload)
    assert res.status_code == 422