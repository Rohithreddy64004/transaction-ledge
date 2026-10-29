from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import TypedDict


class TransactionType(str, Enum):
    credit = "credit"
    debit = "debit"


class AccountDoc(TypedDict):
    _id: str
    name: str
    balance: Decimal
    created_at: str


class TransactionDoc(TypedDict):
    _id: str
    account_id: str
    type: str
    amount: Decimal
    description: str
    reference_id: str
    created_at: str


class TransferDoc(TypedDict):
    _id: str
    source_account_id: str
    destination_account_id: str
    amount: Decimal
    reference_id: str
    description: str
    created_at: str
