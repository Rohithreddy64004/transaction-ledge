from __future__ import annotations

import asyncio
from decimal import Decimal

from mongomock_motor import AsyncMongoMockClient

from app.services import create_account, create_transaction, get_account_or_404


def test_credit_and_debit_flow(client):
    account = client.post("/api/accounts/", json={"name": "A"}).json()
    credit = client.post(f"/api/accounts/{account['id']}/transactions/", json={
        "type": "credit",
        "amount": "100.00",
        "description": "deposit",
        "reference_id": "TXN-001",
    })
    assert credit.status_code == 201, credit.text
    assert client.get(f"/api/accounts/{account['id']}/balance").json()["balance"] == "100.00"
    debit = client.post(f"/api/accounts/{account['id']}/transactions/", json={
        "type": "debit",
        "amount": "30.00",
        "description": "withdraw",
        "reference_id": "TXN-002",
    })
    assert debit.status_code == 201, debit.text
    assert client.get(f"/api/accounts/{account['id']}/balance").json()["balance"] == "70.00"


def test_duplicate_reference_is_rejected(client):
    account = client.post("/api/accounts/", json={"name": "A"}).json()
    payload = {"type": "credit", "amount": "50.00", "description": "dup", "reference_id": "DUP-1"}
    first = client.post(f"/api/accounts/{account['id']}/transactions/", json=payload)
    second = client.post(f"/api/accounts/{account['id']}/transactions/", json=payload)
    assert first.status_code == 201
    assert second.status_code == 409
    assert client.get(f"/api/accounts/{account['id']}/balance").json()["balance"] == "50.00"


def test_insufficient_funds_rejected(client):
    account = client.post("/api/accounts/", json={"name": "A"}).json()
    response = client.post(f"/api/accounts/{account['id']}/transactions/", json={
        "type": "debit",
        "amount": "10.00",
        "description": "bad",
        "reference_id": "TXN-099",
    })
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INSUFFICIENT_FUNDS"


def test_invalid_transaction_input_rejected(client):
    account = client.post("/api/accounts/", json={"name": "A"}).json()
    response = client.post(f"/api/accounts/{account['id']}/transactions/", json={"type": "transfer", "amount": "10.00", "description": "bad", "reference_id": "R1"})
    assert response.status_code == 422


def test_amount_with_more_than_two_decimal_places_is_rejected(client):
    account = client.post("/api/accounts/", json={"name": "precision"}).json()
    response = client.post(
        f"/api/accounts/{account['id']}/transactions/",
        json={
            "type": "credit",
            "amount": "10.999",
            "description": "invalid precision",
            "reference_id": "PRECISION-1",
        },
    )
    assert response.status_code == 422


def test_concurrent_debits_never_make_balance_negative_in_mock_harness():
    async def exercise():
        db = AsyncMongoMockClient()["concurrency_test"]
        account = await create_account(db, "concurrent")
        await create_transaction(
            db,
            account["_id"],
            {
                "type": "credit",
                "amount": Decimal("100.00"),
                "description": "seed",
                "reference_id": "CONCURRENT-SEED",
            },
        )

        async def debit(index: int):
            try:
                await create_transaction(
                    db,
                    account["_id"],
                    {
                        "type": "debit",
                        "amount": Decimal("60.00"),
                        "description": "concurrent debit",
                        "reference_id": f"CONCURRENT-{index}",
                    },
                )
                return "success"
            except Exception as exc:
                return type(exc).__name__

        results = await asyncio.gather(*(debit(index) for index in range(3)))
        final_account = await get_account_or_404(db, account["_id"])
        assert final_account["balance"].to_decimal() >= 0
        assert results.count("success") <= 1

    asyncio.run(exercise())
