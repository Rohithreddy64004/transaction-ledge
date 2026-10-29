from __future__ import annotations


def test_history_returns_paginated_results(client):
    account = client.post("/api/accounts/", json={"name": "acct"}).json()
    client.post(f"/api/accounts/{account['id']}/transactions/", json={"type": "credit", "amount": "10.00", "description": "c1", "reference_id": "C1"})
    client.post(f"/api/accounts/{account['id']}/transactions/", json={"type": "credit", "amount": "15.00", "description": "c2", "reference_id": "C2"})
    client.post(f"/api/accounts/{account['id']}/transactions/", json={"type": "debit", "amount": "5.00", "description": "d1", "reference_id": "D1"})
    response = client.get(f"/api/accounts/{account['id']}/transactions/?page=1&limit=2")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total_records"] == 3
    assert data["page_size"] == 2
    assert len(data["results"]) == 2
    assert data["results"][0]["reference_id"] in {"D1", "C2"}


def test_invalid_pagination_is_rejected(client):
    account = client.post("/api/accounts/", json={"name": "acct"}).json()
    assert client.get(f"/api/accounts/{account['id']}/transactions/?page=0").status_code == 422
    assert client.get(f"/api/accounts/{account['id']}/transactions/?limit=0").status_code == 422
    assert client.get(f"/api/accounts/{account['id']}/transactions/?limit=999").status_code == 422


def test_transaction_history_has_no_mutation_routes(client):
    account = client.post("/api/accounts/", json={"name": "immutable"}).json()
    transaction = client.post(
        f"/api/accounts/{account['id']}/transactions/",
        json={
            "type": "credit",
            "amount": "10.00",
            "description": "immutable",
            "reference_id": "IMMUTABLE-1",
        },
    ).json()
    transaction_url = f"/api/accounts/{account['id']}/transactions/{transaction['id']}"
    assert client.put(transaction_url, json={"amount": "99.99"}).status_code == 404
    assert client.delete(transaction_url).status_code == 404
    assert client.get(f"/api/accounts/{account['id']}/balance").json()["balance"] == "10.00"


def test_history_supports_search_and_date_filters(client):
    account = client.post("/api/accounts/", json={"name": "searchable"}).json()
    client.post(
        f"/api/accounts/{account['id']}/transactions/",
        json={"type": "credit", "amount": "12.50", "description": "Salary credit", "reference_id": "SEARCH-SALARY"},
    )
    client.post(
        f"/api/accounts/{account['id']}/transactions/",
        json={"type": "debit", "amount": "2.50", "description": "Coffee", "reference_id": "SEARCH-COFFEE"},
    )
    search_response = client.get(
        f"/api/accounts/{account['id']}/transactions/?search=salary&page=1&limit=10"
    )
    assert search_response.status_code == 200
    assert search_response.json()["total_records"] == 1
    assert search_response.json()["results"][0]["reference_id"] == "SEARCH-SALARY"

    date_response = client.get(
        f"/api/accounts/{account['id']}/transactions/?date_from=2000-01-01T00:00:00%2B00:00&date_to=2000-01-02T00:00:00%2B00:00&page=1&limit=10"
    )
    assert date_response.status_code == 200
    assert date_response.json()["total_records"] == 0
