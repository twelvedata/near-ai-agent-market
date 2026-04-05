import os
import pytest
from fastapi.testclient import TestClient

# Set env vars before importing app so module-level os.getenv() picks them up
os.environ.setdefault("TWELVE_DATA_API_KEY", "test-td-key")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("PROXY_SECRET", "test-secret")

from main import app  # noqa: E402


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-secret"}
