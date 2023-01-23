from ipaddress import IPv4Address
from pydantic import BaseModel
from uuid import UUID
from decimal import Decimal
from datetime import datetime


class TransactionRequestObject(BaseModel):
    transaction_id: UUID
    own_bank_ip: str
    other_bank_ip: str
    own_account_id: UUID
    other_account_id: UUID
    amount: Decimal
    comment: str | None


class TransactionPostObject(BaseModel):
    transaction_id: UUID
    origin_id: UUID
    destination_id: UUID
    amount: Decimal
    comment: str | None


class LedgerObject(BaseModel):
    transaction_id: UUID
    origin: UUID
    destination: UUID
    loan_id: None
    amount: Decimal
    timestamp: Decimal
    comment: str | None
