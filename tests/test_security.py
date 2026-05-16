import pytest
from fastapi import HTTPException
from app.core.security import verify_api_key
from app.core.config import settings

def test_verify_api_key_valid():
    # Should return the api key if it matches settings
    result = verify_api_key(api_key=settings.API_KEY)
    assert result == settings.API_KEY

def test_verify_api_key_invalid():
    # Should raise 401 if it doesn't match
    with pytest.raises(HTTPException) as excinfo:
        verify_api_key(api_key="wrong_key")
    assert excinfo.value.status_code == 401
    assert excinfo.value.detail == "Invalid API Key"
