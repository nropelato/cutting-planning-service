from pydantic import BaseModel, Field
from typing import Dict, List, Optional

class CutRequest(BaseModel):
    demand_data: Dict[str, Dict[str, int]] = Field(..., description="Maps 'Colorway' -> {'Size': Quantity}")
    table_length_cm: int = Field(..., gt=0)
    fabric_width_cm: int = Field(..., gt=0)
    nesting_efficiency: float = Field(0.85, gt=0.0, le=1.0)
    
    # Dynamic Tolerance Inputs with defaults from settings
    max_shortage_pct: float = Field(0.05, ge=0.0, le=0.20)
    shortage_penalty_multiplier: float = Field(1.5, ge=1.0)
    
    # Anomaly Gate Controllers (Optional - falls back to system defaults)
    anomaly_scaling_pct: Optional[float] = None
    hard_anomaly_ceiling: Optional[int] = None
    
    cost_per_size: Optional[Dict[str, int]] = None
    area_per_size_cm2: Optional[Dict[str, int]] = None

class InferenceRequest(BaseModel):
    demand_data: Dict[str, Dict[str, int]]
    input_markers: List[Dict[str, float]] = Field(..., description="Array of existing CAD marker size templates")

class MarkerResult(BaseModel):
    marker_id: str
    layout: Dict[str, float]
    spreading_layers: int
    table_length_used_cm: float = 0.0
    utilization_pct: float = 0.0

class OptimizationResponse(BaseModel):
    status: str
    solve_time_ms: float
    total_financial_waste: float
    markers: List[MarkerResult]
