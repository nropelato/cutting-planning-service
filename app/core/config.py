from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Security Configurations
    API_KEY: str = "super_secret_dev_key_change_in_production"
    ALLOWED_CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    
    # Engine Architectural Constraints
    MAX_PATTERNS: int = 3
    MAX_PLY_LIMIT: int = 100
    SOLVER_TIME_LIMIT_SECONDS: float = 30.0
    
    # Financial-Industrial TCO Parameters
    LAYER_SPREADING_COST: float = 15.00     # Pegged to labor minutes
    MARKER_FIXED_BASE_COST: float = 80.00   # CAD labor / nesting setup
    MARKER_PAPER_COST_PER_CM: float = 0.15  # R$ 15.00 per linear meter of paper/ink
    SUBSTITUTION_ANNOYANCE_TAX: float = 2.00 # Small "delta" to discourage unnecessary downgrades
    
    # Short-Shipping Tolerance Gates
    MAX_SHORTAGE_PCT: float = 0.05          # Maximum 5% underproduction allowed per size
    SHORTAGE_PENALTY_MULTIPLIER: float = 1.5 # Shortage penalty = 150% of the fabric cost
    
    # Default Anomaly Tuning Knobs
    DEFAULT_ANOMALY_SCALING_PCT: float = 0.02  # 2% of the anchor size
    DEFAULT_HARD_ANOMALY_CEILING: int = 3      # Never eliminate more than 3 pieces blindly

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
