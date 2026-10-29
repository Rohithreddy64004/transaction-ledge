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
