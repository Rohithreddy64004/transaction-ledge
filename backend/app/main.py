from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pymongo.errors import DuplicateKeyError

from app.config import get_settings
from app.database import lifespan
from app.exceptions import LedgerError, integrity_error_handler, ledger_error_handler, validation_error_handler
from app.schemas import AccountBalance, AccountCreate, AccountRead, TransactionCreate, TransactionHistoryResponse, TransactionRead, TransferCreate, TransferRead
from app.services import create_account, create_transaction, create_transfer, db_decimal, get_account_or_404, get_transaction_history, list_accounts, normalize_transaction_type


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    async for _ in lifespan(app):
        yield


def create_app() -> FastAPI:
    app = FastAPI(title="Transaction Ledger API", version="1.0.0", lifespan=app_lifespan)
    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in settings.frontend_origins.split(",") if origin.strip()],
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
    app.add_exception_handler(LedgerError, ledger_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(DuplicateKeyError, integrity_error_handler)

    @app.get("/health")
    async def health(request: Request):
        await request.app.state.mongodb.command({"ping": 1})
        return {"status": "ok"}

    @app.post("/api/accounts/", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
    async def create_account_endpoint(payload: AccountCreate, request: Request):
        account = await create_account(request.app.state.mongodb, payload.name)
        return {"id": account["_id"], "name": account["name"], "balance": db_decimal(account["balance"]), "created_at": account["created_at"]}

    @app.get("/api/accounts/", response_model=list[AccountRead])
    async def list_accounts_endpoint(request: Request):
        accounts = await list_accounts(request.app.state.mongodb)
        return [
            {"id": account["_id"], "name": account["name"], "balance": db_decimal(account["balance"]), "created_at": account["created_at"]}
            for account in accounts
        ]

    @app.get("/api/accounts/{account_id}/balance", response_model=AccountBalance)
    async def get_balance(account_id: str, request: Request):
        account = await get_account_or_404(request.app.state.mongodb, account_id)
        return {"account_id": account["_id"], "balance": db_decimal(account["balance"])}

    @app.post("/api/accounts/{account_id}/transactions/", response_model=TransactionRead, status_code=status.HTTP_201_CREATED)
    async def create_transaction_endpoint(account_id: str, payload: TransactionCreate, request: Request):
        transaction = await create_transaction(request.app.state.mongodb, account_id, payload.model_dump())
        return {
            "id": transaction["_id"],
            "account_id": transaction["account_id"],
            "type": transaction["type"],
            "amount": db_decimal(transaction["amount"]),
            "description": transaction["description"],
            "reference_id": transaction["reference_id"],
            "created_at": transaction["created_at"],
        }

    @app.get("/api/accounts/{account_id}/transactions/", response_model=TransactionHistoryResponse)
    async def list_transactions(
        account_id: str,
        request: Request,
        type: str | None = Query(default=None, alias="type"),
        search: str | None = Query(default=None, min_length=1, max_length=100),
        date_from: str | None = Query(default=None, min_length=10, max_length=30),
        date_to: str | None = Query(default=None, min_length=10, max_length=30),
        page: int = Query(default=1, ge=1),
        limit: int = Query(default=10, ge=1),
    ):
        max_limit = get_settings().max_page_size
        if limit > max_limit:
            raise LedgerError(422, "INVALID_PAGINATION", f"limit must be between 1 and {max_limit}.")
        if type is not None:
            normalize_transaction_type(type)
        history = await get_transaction_history(
            request.app.state.mongodb,
            account_id,
            type,
            page,
            limit,
            search=search,
            date_from=date_from,
            date_to=date_to,
        )
        return {
            "account_id": history["account_id"],
            "current_page": history["current_page"],
            "page_size": history["page_size"],
            "total_records": history["total_records"],
            "total_pages": history["total_pages"],
            "results": history["results"],
        }

    @app.post("/api/transfers/", response_model=TransferRead, status_code=status.HTTP_201_CREATED)
    async def create_transfer_endpoint(payload: TransferCreate, request: Request):
        transfer = await create_transfer(request.app.state.mongodb, payload.model_dump())
        return {
            "id": transfer["_id"],
            "source_account_id": transfer["source_account_id"],
            "destination_account_id": transfer["destination_account_id"],
            "amount": db_decimal(transfer["amount"]),
            "reference_id": transfer["reference_id"],
            "description": transfer["description"],
            "created_at": transfer["created_at"],
        }

    return app


app = create_app()
