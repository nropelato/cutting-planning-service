from pydantic import BaseModel, Field
from typing import Dict, List, Optional

class CutRequest(BaseModel):
    demand_data: Dict[str, Dict[str, int]] = Field(
        ..., 
        example={"REF-2020/BRANCO": {"P": 12, "M": 25, "G": 35, "G3": 1}},
        description="Nested dictionary structure mapping (Reference/Colorway) to Size:Quantity pairs."
    )
    table_length_cm: int = Field(
        800, 
        gt=0, 
        description="The strict physical length capacity of the spreading table ironwork."
    )
    fabric_width_cm: int = Field(
        180, 
        gt=0, 
        description="The net usable cross-feed cutting width of the fabric roll (excluding selvedges)."
    )
    nesting_efficiency: float = Field(
        0.85, 
        gt=0.0, 
        le=1.0, 
        description="The historical CAD nesting multiplier tracking fabric panel yield vs interstitial scrap."
    )
    
    # --- ANOMALY GATE PARAMETERS ---
    anomaly_scaling_pct: float = Field(
        0.02, 
        ge=0.0, 
        le=0.10, 
        description="Dynamic sensitivity gate. Defines the anomaly threshold as a percentage of the highest-demand (Anchor) size in the batch."
    )
    hard_anomaly_ceiling: int = Field(
        3, 
        ge=0, 
        le=10, 
        description="The hard maximum integer cutoff for anomaly classification. Prevents size erasure on mass-production batches."
    )
    
    # --- FULFILLMENT TOLERANCE PARAMETERS ---
    max_shortage_pct: float = Field(
        0.05, 
        ge=0.0, 
        le=0.20, 
        description="The global commercial underproduction margin allowed across the entire multi-colorway batch."
    )
    shortage_penalty_multiplier: float = Field(
        1.5, 
        ge=1.0, 
        description="The financial scale factor applied to unfulfilled items. Evaluated as (Fabric Cost * Multiplier) in the TCO function."
    )
    
    cost_per_size: Optional[Dict[str, int]] = Field(
        None, 
        description="Optional override matrix mapping Size to its literal raw fabric cost."
    )
    area_per_size_cm2: Optional[Dict[str, int]] = Field(
        None, 
        description="Optional override matrix mapping Size to its exact net geometric square-centimeter footprint."
    )

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
