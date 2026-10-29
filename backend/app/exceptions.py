from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pymongo.errors import DuplicateKeyError


class LedgerError(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: Any | None = None):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


class AccountNotFoundError(LedgerError):
    def __init__(self, account_id: str):
        super().__init__(404, "ACCOUNT_NOT_FOUND", f"Account {account_id} was not found.")


class InvalidTransactionError(LedgerError):
    def __init__(self, message: str):
        super().__init__(422, "INVALID_TRANSACTION", message)


class InsufficientFundsError(LedgerError):
    def __init__(self):
        super().__init__(400, "INSUFFICIENT_FUNDS", "The account has insufficient funds.")


class DuplicateTransactionError(LedgerError):
    def __init__(self, reference_id: str):
        super().__init__(409, "DUPLICATE_REFERENCE", f"Reference '{reference_id}' already exists for this account.")


class DuplicateTransferError(LedgerError):
    def __init__(self, reference_id: str):
        super().__init__(409, "DUPLICATE_TRANSFER", f"Transfer reference '{reference_id}' already exists.")


def json_error(status_code: int, code: str, message: str, details: Any | None = None) -> JSONResponse:
    payload: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details is not None:
        payload["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=payload)


async def ledger_error_handler(_: Request, exc: LedgerError) -> JSONResponse:
    return json_error(exc.status_code, exc.code, exc.message, exc.details)


async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else "Request failed."
    return json_error(exc.status_code, "HTTP_ERROR", detail)


async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    details = []
    for error in exc.errors():
        loc = ".".join(str(part) for part in error.get("loc", ()))
        details.append({"field": loc, "message": error.get("msg", "Invalid input")})
    return json_error(422, "VALIDATION_ERROR", "Request validation failed.", details)


async def integrity_error_handler(_: Request, exc: DuplicateKeyError) -> JSONResponse:
    return json_error(409, "DATABASE_CONFLICT", "The request conflicts with existing data.")
