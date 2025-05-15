import os

import pytest
from app.main import app
from fastapi.testclient import TestClient

os.environ["ENV_FILE"] = ".env.test"


@pytest.fixture
def client():
    return TestClient(app)
