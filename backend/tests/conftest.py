from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

from app.main import app


@pytest.fixture
def client(monkeypatch):
    mock_client = AsyncMongoMockClient()
    db = mock_client["test_ledger"]
    monkeypatch.setenv("MONGODB_URL", "mongodb://localhost:27017")
    monkeypatch.setenv("MONGODB_DATABASE", "test_ledger")
    app.state.mongo_client = mock_client
    app.state.mongodb = db
    with TestClient(app) as test_client:
        yield test_client
