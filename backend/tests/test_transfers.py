from __future__ import annotations


def test_transfer_success(client):
    source = client.post("/api/accounts/", json={"name": "source"}).json()
    destination = client.post("/api/accounts/", json={"name": "destination"}).json()
    client.post(f"/api/accounts/{source['id']}/transactions/", json={"type": "credit", "amount": "100.00", "description": "topup", "reference_id": "TOPUP"})
    response = client.post('/api/transfers/', json={"source_account_id": source['id'], "destination_account_id": destination['id'], "amount": "30.00", "reference_id": "T-1", "description": "transfer"})
    assert response.status_code == 201, response.text
    assert response.json()['reference_id'] == 'T-1'
    assert client.get(f"/api/accounts/{source['id']}/balance").json()['balance'] == '70.00'
    assert client.get(f"/api/accounts/{destination['id']}/balance").json()['balance'] == '30.00'


def test_transfer_duplicate_is_rejected(client):
    source = client.post("/api/accounts/", json={"name": "source"}).json()
    destination = client.post("/api/accounts/", json={"name": "destination"}).json()
    client.post(f"/api/accounts/{source['id']}/transactions/", json={"type": "credit", "amount": "100.00", "description": "topup", "reference_id": "TOPUP"})
    payload = {"source_account_id": source['id'], "destination_account_id": destination['id'], "amount": "10.00", "reference_id": "T-1", "description": "transfer"}
    assert client.post('/api/transfers/', json=payload).status_code == 201
    assert client.post('/api/transfers/', json=payload).status_code == 409


def test_same_account_transfer_rejected(client):
    account = client.post('/api/accounts/', json={'name': 'acct'}).json()
    response = client.post('/api/transfers/', json={'source_account_id': account['id'], 'destination_account_id': account['id'], 'amount': '10.00', 'reference_id': 'T-2', 'description': 'bad'})
    assert response.status_code == 422
