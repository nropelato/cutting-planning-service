from app.core.config import Settings, settings

def test_settings_defaults():
    # Test default values
    assert settings.MAX_PATTERNS == 3
    assert settings.MAX_PLY_LIMIT == 100
    assert settings.SOLVER_TIME_LIMIT_SECONDS == 30.0
    assert settings.LAYER_TIME_PENALTY == 5
    assert settings.PATTERN_USAGE_PENALTY == 200
    assert settings.DOWNGRADE_PENALTY == 15

def test_settings_env_override(monkeypatch):
    # Mock environment variable override
    monkeypatch.setenv("MAX_PATTERNS", "10")
    new_settings = Settings()
    assert new_settings.MAX_PATTERNS == 10
