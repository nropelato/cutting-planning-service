import time
from fastapi import APIRouter, Depends, HTTPException
from app.core.security import verify_api_key
from app.core.config import settings
from app.models.schemas import CutRequest, OptimizationResponse, MarkerResult
from app.services.optimization import run_manufacturing_optimization, ProductionConfig

router = APIRouter()

@router.post("/optimize", response_model=OptimizationResponse)
async def optimize_cut_job(request: CutRequest, api_key: str = Depends(verify_api_key)):
    try:
        start_time = time.time()
        # Resolve dynamic overrides vs baseline defaults
        anomaly_pct = request.anomaly_scaling_pct if request.anomaly_scaling_pct is not None else settings.DEFAULT_ANOMALY_SCALING_PCT
        anomaly_ceil = request.hard_anomaly_ceiling if request.hard_anomaly_ceiling is not None else settings.DEFAULT_HARD_ANOMALY_CEILING

        # Map physical parameters
        config = ProductionConfig()
        config.MAX_TABLE_LENGTH_CM = request.table_length_cm
        config.FABRIC_WIDTH_CM = request.fabric_width_cm
        config.NESTING_EFFICIENCY = request.nesting_efficiency
        config.MAX_PATTERNS = settings.MAX_PATTERNS
        config.MAX_PLY_LIMIT = settings.MAX_PLY_LIMIT
        config.SOLVER_TIME_LIMIT_SECONDS = settings.SOLVER_TIME_LIMIT_SECONDS
        
        if request.cost_per_size: config.COST_PER_SIZE = request.cost_per_size
        if request.area_per_size_cm2: config.AREA_PER_SIZE_CM2 = request.area_per_size_cm2

        # Execute bounded solver run
        solver_output = run_manufacturing_optimization(
            request.demand_data, 
            config,
            anomaly_pct,
            anomaly_ceil
        )
        solve_time_ms = round((time.time() - start_time) * 1000, 2)

        if solver_output["status"] not in ["OPTIMAL", "FEASIBLE"]:
            raise HTTPException(status_code=422, detail=f"Solver Failure: {solver_output['status']}")

        return OptimizationResponse(
            status=solver_output["status"],
            solve_time_ms=solve_time_ms,
            total_financial_waste=solver_output["financial_waste"],
            markers=[MarkerResult(marker_id=f"MKR-{i+1:03d}", **mkr) for i, mkr in enumerate(solver_output["markers"])]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
