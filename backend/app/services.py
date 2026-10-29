from __future__ import annotations

import uuid
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from bson import Decimal128
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.exceptions import AccountNotFoundError, DuplicateTransactionError, DuplicateTransferError, InsufficientFundsError, InvalidTransactionError
from app.models import TransactionType


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def decimal_to_db(value: Decimal) -> Decimal128:
    return Decimal128(value)


def db_decimal(value: Decimal128 | Decimal | None) -> Decimal:
    if value is None:
        return Decimal("0.00")
    if isinstance(value, Decimal128):
        return value.to_decimal()
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def normalize_amount(value: Decimal | str) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise InvalidTransactionError("amount must be a valid decimal value.") from exc
    if not amount.is_finite():
        raise InvalidTransactionError("amount must be a valid decimal value.")
    if amount <= 0:
        raise InvalidTransactionError("amount must be greater than zero.")
    if amount.as_tuple().exponent < -2:
        raise InvalidTransactionError("amount cannot have more than 2 decimal places.")
    return amount.quantize(Decimal("0.01"))


def normalize_transaction_type(raw_type: str) -> TransactionType:
    try:
        return TransactionType(raw_type)
    except ValueError as exc:
        raise InvalidTransactionError("Transaction type must be either 'credit' or 'debit'.") from exc


async def get_account_or_404(db: AsyncIOMotorDatabase, account_id: str) -> dict:
    account = await db.accounts.find_one({"_id": account_id})
    if account is None:
        raise AccountNotFoundError(account_id)
    return account


async def create_account(db: AsyncIOMotorDatabase, name: str) -> dict:
    account_id = f"acc_{uuid.uuid4().hex}"
    account = {
        "_id": account_id,
        "name": name.strip(),
        "balance": decimal_to_db(Decimal("0.00")),
        "created_at": utc_now().isoformat(),
    }
    await db.accounts.insert_one(account)
    return account


async def list_accounts(db: AsyncIOMotorDatabase) -> list[dict]:
    accounts = []
    async for account in db.accounts.find({}, sort=[("created_at", 1)]):
        accounts.append(account)
    return accounts


async def create_transaction(db: AsyncIOMotorDatabase, account_id: str, payload: dict) -> dict:
    amount = normalize_amount(payload["amount"])
    txn_type = normalize_transaction_type(payload["type"])
    reference_id = str(payload["reference_id"]).strip()
    description = str(payload["description"]).strip()
    if not reference_id:
        raise InvalidTransactionError("reference_id must not be blank.")
    if not description:
        raise InvalidTransactionError("description must not be blank.")

    async def _perform(session=None, atomic_balance_update=True):
        query_kwargs = {"session": session} if session is not None else {}
        account = await db.accounts.find_one({"_id": account_id}, **query_kwargs)
        if account is None:
            raise AccountNotFoundError(account_id)
        if await db.transactions.find_one({"account_id": account_id, "reference_id": reference_id}, **query_kwargs):
            raise DuplicateTransactionError(reference_id)

        update_kwargs = {"session": session} if session is not None else {}
        if atomic_balance_update:
            balance_filter = {"_id": account_id}
            if txn_type == TransactionType.debit:
                balance_filter["balance"] = {"$gte": decimal_to_db(amount)}
                balance_update = {"$inc": {"balance": decimal_to_db(-amount)}}
            else:
                balance_update = {"$inc": {"balance": decimal_to_db(amount)}}
            update_result = await db.accounts.update_one(balance_filter, balance_update, **update_kwargs)
            if update_result.modified_count != 1:
                raise InsufficientFundsError()
        else:
            current_balance = db_decimal(account.get("balance"))
            if txn_type == TransactionType.debit and current_balance < amount:
                raise InsufficientFundsError()
            updated_balance = current_balance + amount if txn_type == TransactionType.credit else current_balance - amount
            await db.accounts.update_one(
                {"_id": account_id},
                {"$set": {"balance": decimal_to_db(updated_balance)}},
                **update_kwargs,
            )
        transaction = {
            "_id": f"txn_{uuid.uuid4().hex}",
            "account_id": account_id,
            "type": txn_type.value,
            "amount": decimal_to_db(amount),
            "description": description,
            "reference_id": reference_id,
            "created_at": utc_now().isoformat(),
        }
        insert_kwargs = {"session": session} if session is not None else {}
        await db.transactions.insert_one(transaction, **insert_kwargs)
        return transaction

    client = db.client
    try:
        async with await client.start_session() as session:
            session.start_transaction()
            try:
                result = await _perform(session)
                await session.commit_transaction()
                return result
            except Exception:
                await session.abort_transaction()
                raise
    except NotImplementedError:
        return await _perform(atomic_balance_update=False)


async def get_transaction_history(
    db: AsyncIOMotorDatabase,
    account_id: str,
    transaction_type: str | None,
    page: int,
    page_size: int,
    *,
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    await get_account_or_404(db, account_id)
    query: dict = {"account_id": account_id}
    if transaction_type is not None:
        query["type"] = normalize_transaction_type(transaction_type).value
    if search:
        query["$or"] = [
            {"description": {"$regex": re.escape(search), "$options": "i"}},
            {"reference_id": {"$regex": re.escape(search), "$options": "i"}},
        ]
    if date_from or date_to:
        query["created_at"] = {}
        if date_from:
            query["created_at"]["$gte"] = date_from
        if date_to:
            query["created_at"]["$lte"] = date_to
    total_records = await db.transactions.count_documents(query)
    skip = (page - 1) * page_size
    cursor = db.transactions.find(query).sort([("created_at", -1), ("_id", -1)]).skip(skip).limit(page_size)
    results = []
    async for item in cursor:
        results.append({
            "id": item["_id"],
            "account_id": item["account_id"],
            "type": item["type"],
            "amount": db_decimal(item["amount"]),
            "description": item["description"],
            "reference_id": item["reference_id"],
            "created_at": item["created_at"],
        })
    total_pages = (total_records + page_size - 1) // page_size if total_records else 0
    return {
        "account_id": account_id,
        "current_page": page,
        "page_size": page_size,
        "total_records": total_records,
        "total_pages": total_pages,
        "results": results,
    }


async def create_transfer(db: AsyncIOMotorDatabase, payload: dict) -> dict:
    source_account_id = payload["source_account_id"]
    destination_account_id = payload["destination_account_id"]
    amount = normalize_amount(payload["amount"])
    reference_id = str(payload["reference_id"]).strip()
    description = str(payload["description"]).strip()
    if not reference_id:
        raise InvalidTransactionError("reference_id must not be blank.")
    if source_account_id == destination_account_id:
        raise InvalidTransactionError("Source and destination account IDs must be different.")

    async def _perform(session=None, atomic_balance_update=True):
        query_kwargs = {"session": session} if session is not None else {}
        if await db.transfers.find_one({"reference_id": reference_id}, **query_kwargs):
            raise DuplicateTransferError(reference_id)

        source = await db.accounts.find_one({"_id": source_account_id}, **query_kwargs)
        destination = await db.accounts.find_one({"_id": destination_account_id}, **query_kwargs)
        if source is None:
            raise AccountNotFoundError(source_account_id)
        if destination is None:
            raise AccountNotFoundError(destination_account_id)

        update_kwargs = {"session": session} if session is not None else {}
        if atomic_balance_update:
            source_update = await db.accounts.update_one(
                {"_id": source_account_id, "balance": {"$gte": decimal_to_db(amount)}},
                {"$inc": {"balance": decimal_to_db(-amount)}},
                **update_kwargs,
            )
            if source_update.modified_count != 1:
                raise InsufficientFundsError()
            await db.accounts.update_one(
                {"_id": destination_account_id},
                {"$inc": {"balance": decimal_to_db(amount)}},
                **update_kwargs,
            )
        else:
            source_balance = db_decimal(source.get("balance"))
            destination_balance = db_decimal(destination.get("balance"))
            if source_balance < amount:
                raise InsufficientFundsError()
            await db.accounts.update_one(
                {"_id": source_account_id},
                {"$set": {"balance": decimal_to_db(source_balance - amount)}},
                **update_kwargs,
            )
            await db.accounts.update_one(
                {"_id": destination_account_id},
                {"$set": {"balance": decimal_to_db(destination_balance + amount)}},
                **update_kwargs,
            )

        transfer = {
            "_id": f"transfer_{uuid.uuid4().hex}",
            "source_account_id": source_account_id,
            "destination_account_id": destination_account_id,
            "amount": decimal_to_db(amount),
            "reference_id": reference_id,
            "description": description,
            "created_at": utc_now().isoformat(),
        }
        insert_kwargs = {"session": session} if session is not None else {}
        await db.transfers.insert_one(transfer, **insert_kwargs)

        source_transaction = {
            "_id": f"txn_{uuid.uuid4().hex}",
            "account_id": source_account_id,
            "type": TransactionType.debit.value,
            "amount": decimal_to_db(amount),
            "description": f"Transfer to account {destination_account_id}: {description}",
            "reference_id": f"transfer:{reference_id}:source",
            "created_at": utc_now().isoformat(),
        }
        destination_transaction = {
            "_id": f"txn_{uuid.uuid4().hex}",
            "account_id": destination_account_id,
            "type": TransactionType.credit.value,
            "amount": decimal_to_db(amount),
            "description": f"Transfer from account {source_account_id}: {description}",
            "reference_id": f"transfer:{reference_id}:destination",
            "created_at": utc_now().isoformat(),
        }
        await db.transactions.insert_one(source_transaction, **insert_kwargs)
        await db.transactions.insert_one(destination_transaction, **insert_kwargs)
        return transfer

    client = db.client
    try:
        async with await client.start_session() as session:
            session.start_transaction()
            try:
                result = await _perform(session)
                await session.commit_transaction()
                return result
            except Exception:
                await session.abort_transaction()
                raise
    except NotImplementedError:
        return await _perform(atomic_balance_update=False)
