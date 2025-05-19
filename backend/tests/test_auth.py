def test_signup_and_whoami(client):
    # create account
    resp = client.post("/signup", json={"name": "TestCo"})
    assert resp.status_code == 200
    data = resp.json()
    api_key = data["api_key"]

    # auth header
    headers = {"Authorization": f"Bearer {api_key}"}
    me = client.get("/me", headers=headers).json()
    assert me["name"] == "TestCo"
