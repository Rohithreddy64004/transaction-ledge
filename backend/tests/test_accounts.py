from __future__ import annotations


def test_account_creation_and_balance(client):
    response = client.post("/api/accounts/", json={"name": "Rohith Reddy"})
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["name"] == "Rohith Reddy"
    assert data["balance"] == "0.00"
    assert client.get(f"/api/accounts/{data['id']}/balance").json()["balance"] == "0.00"


def test_missing_name_is_rejected(client):
    response = client.post("/api/accounts/", json={"name": "   "})
    assert response.status_code == 422


def test_client_cannot_set_initial_balance(client):
    response = client.post("/api/accounts/", json={"name": "test", "balance": "999.99"})
    assert response.status_code == 422


def test_accounts_can_be_listed_for_transfer_selection(client):
    first = client.post("/api/accounts/", json={"name": "Sender"}).json()
    second = client.post("/api/accounts/", json={"name": "Recipient"}).json()
    response = client.get("/api/accounts/")
    assert response.status_code == 200
    assert {item["id"] for item in response.json()} >= {first["id"], second["id"]}
    assert all("balance" in item for item in response.json())
