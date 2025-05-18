import pytest
from app.db import models
from app.db.session import engine
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    models.Base.metadata.drop_all(bind=engine)
    models.Base.metadata.create_all(bind=engine)
    yield
    models.Base.metadata.drop_all(bind=engine)


def test_signup_and_whoami():
    # create account
    resp = client.post("/signup", json={"name": "TestCo"})
    assert resp.status_code == 200
    data = resp.json()
    api_key = data["api_key"]

    # auth header
    headers = {"Authorization": f"Bearer {api_key}"}
    me = client.get("/me", headers=headers).json()
    assert me["name"] == "TestCo"
