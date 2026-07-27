"""Schemas de créditos y planes."""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel


class PlanRead(BaseModel):
    id: int
    nombre: str
    credits_monthly: int
    price: float
    features: Optional[Any] = None
    activo: bool = True

    model_config = {"from_attributes": True}


class CreditLedgerRead(BaseModel):
    id: int
    user_id: int
    delta: int
    reason: str
    balance_after: int
    fecha: datetime

    model_config = {"from_attributes": True}


class CreditsBalance(BaseModel):
    user_id: int
    balance: int
    plan: Optional[PlanRead] = None
    ledger: List[CreditLedgerRead] = []
