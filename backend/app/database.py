from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import get_settings


def create_mongo_client(url: str) -> AsyncIOMotorClient:
    return AsyncIOMotorClient(url)


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    await db.accounts.create_index([("name", 1)])
    await db.transactions.create_index([("account_id", 1), ("reference_id", 1)], unique=True)
    await db.transactions.create_index([("account_id", 1), ("created_at", -1), ("_id", -1)])
    await db.transfers.create_index([("reference_id", 1)], unique=True)


async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    database = getattr(app.state, "mongodb", None)
    client = getattr(app.state, "mongo_client", None)
    owns_client = client is None or database is None

    if owns_client:
        settings = get_settings()
        client = create_mongo_client(settings.mongodb_url)
        database = client[settings.mongodb_database]
        app.state.mongo_client = client
        app.state.mongodb = database

    await ensure_indexes(database)
    try:
        yield
    finally:
        if owns_client and client is not None:
            client.close()
            app.state.mongo_client = None
            app.state.mongodb = None
