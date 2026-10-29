from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AccountCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=1, max_length=200)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name must not be blank")
        return value


class AccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    balance: Decimal
    created_at: str


class TransactionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: str = Field(..., pattern=r"^(credit|debit)$")
    amount: Decimal = Field(..., gt=0, max_digits=18, decimal_places=2)
    description: str = Field(..., min_length=1, max_length=255)
    reference_id: str = Field(..., min_length=1, max_length=255)

    @field_validator("description", "reference_id")
    @classmethod
    def strip_and_validate(cls, value: str, info: Any) -> str:
        value = value.strip()
        if not value:
            raise ValueError(f"{info.field_name} must not be blank")
        return value


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    account_id: str
    type: str
    amount: Decimal
    description: str
    reference_id: str
    created_at: str


class AccountBalance(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    account_id: str
    balance: Decimal


class TransactionHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    account_id: str
    current_page: int
    page_size: int
    total_records: int
    total_pages: int
    results: list[TransactionRead]


class TransferCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_account_id: str
    destination_account_id: str
    amount: Decimal = Field(..., gt=0, max_digits=18, decimal_places=2)
    description: str = Field(..., min_length=1, max_length=255)
    reference_id: str = Field(..., min_length=1, max_length=255)

    @field_validator("description", "reference_id")
    @classmethod
    def strip_and_validate(cls, value: str, info: Any) -> str:
        value = value.strip()
        if not value:
            raise ValueError(f"{info.field_name} must not be blank")
        return value


class TransferRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    source_account_id: str
    destination_account_id: str
    amount: Decimal
    reference_id: str
    description: str
    created_at: str
