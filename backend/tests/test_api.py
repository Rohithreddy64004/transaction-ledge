from __future__ import annotations


def test_smoke(client):
    account = client.post("/api/accounts/", json={"name": "Rohith Reddy"}).json()
    assert account["balance"] == "0.00"
    credit = client.post(f"/api/accounts/{account['id']}/transactions/", json={
        "type": "credit",
        "amount": "100.00",
        "description": "Initial deposit",
        "reference_id": "TXN-001",
    })
    assert credit.status_code == 201
    assert client.get(f"/api/accounts/{account['id']}/balance").json()["balance"] == "100.00"


def test_cors_preflight_allows_firebase_frontend(client):
    response = client.options(
        "/api/accounts/",
        headers={
            "Origin": "https://ledgerly-transaction.web.app",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type,x-requested-with",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://ledgerly-transaction.web.app"
    assert "POST" in response.headers["access-control-allow-methods"]


def test_cors_does_not_grant_unapproved_origin(client):
    response = client.get(
        "/api/accounts/",
        headers={"Origin": "https://unapproved.example.com"},
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
