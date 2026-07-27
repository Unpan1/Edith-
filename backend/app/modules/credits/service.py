"""Planes, saldo y deducción de créditos."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.saas import (
    CreditLedger,
    Plan,
    Subscription,
    SubscriptionStatus,
)
from app.models.user import User
from app.modules.credits.schemas import CreditsBalance, PlanRead
from app.modules.deps import DEFAULT_USER_ID
from app.utils.exceptions import AppError
from app.utils.logger import get_logger

logger = get_logger(__name__)

PROCESS_COST = 10


class CreditsService:
    """Gestión de créditos y bootstrap de plan free."""

    def bootstrap(self, db: Session, user_id: int = DEFAULT_USER_ID) -> None:
        """Asegura usuario, plan free y saldo inicial."""
        user = db.get(User, user_id)
        if not user:
            user = User(
                id=user_id,
                nombre="Admin Local",
                email="admin@clipai.local",
                password="local",
            )
            db.merge(user)
            db.commit()

        free = db.query(Plan).filter(Plan.nombre == "Free").first()
        if not free:
            free = Plan(
                nombre="Free",
                credits_monthly=100,
                price=0.0,
                features=["clips", "content_ai", "thumbnails"],
                activo=True,
            )
            db.add(free)
            db.flush()
            pro = Plan(
                nombre="Pro",
                credits_monthly=500,
                price=29.0,
                features=["todo Free", "automation", "growth_agent"],
                activo=True,
            )
            db.add(pro)
            db.commit()
            db.refresh(free)

        sub = (
            db.query(Subscription)
            .filter(
                Subscription.user_id == user_id,
                Subscription.status == SubscriptionStatus.ACTIVE,
            )
            .first()
        )
        if not sub:
            sub = Subscription(
                user_id=user_id, plan_id=free.id, status=SubscriptionStatus.ACTIVE
            )
            db.add(sub)
            db.commit()

        if self.balance(db, user_id) == 0 and not self._has_any_ledger(db, user_id):
            self.add_credits(db, user_id, free.credits_monthly, "bootstrap_free_plan")

    def _has_any_ledger(self, db: Session, user_id: int) -> bool:
        return (
            db.query(CreditLedger).filter(CreditLedger.user_id == user_id).first()
            is not None
        )

    def balance(self, db: Session, user_id: int = DEFAULT_USER_ID) -> int:
        last = (
            db.query(CreditLedger)
            .filter(CreditLedger.user_id == user_id)
            .order_by(CreditLedger.fecha.desc(), CreditLedger.id.desc())
            .first()
        )
        return last.balance_after if last else 0

    def add_credits(
        self, db: Session, user_id: int, amount: int, reason: str
    ) -> CreditLedger:
        bal = self.balance(db, user_id) + amount
        row = CreditLedger(
            user_id=user_id, delta=amount, reason=reason, balance_after=bal
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    def deduct(
        self, db: Session, user_id: int, amount: int, reason: str
    ) -> CreditLedger:
        bal = self.balance(db, user_id)
        if bal < amount:
            raise AppError(
                f"Créditos insuficientes ({bal} < {amount})", status_code=402
            )
        return self.add_credits(db, user_id, -amount, reason)

    def deduct_for_process(
        self, db: Session, user_id: int = DEFAULT_USER_ID, cost: int = PROCESS_COST
    ) -> CreditLedger:
        return self.deduct(db, user_id, cost, "video_process")

    def list_plans(self, db: Session) -> List[Plan]:
        return db.query(Plan).filter(Plan.activo.is_(True)).all()

    def get_balance_view(self, db: Session, user_id: int = DEFAULT_USER_ID) -> CreditsBalance:
        self.bootstrap(db, user_id)
        sub = (
            db.query(Subscription)
            .filter(
                Subscription.user_id == user_id,
                Subscription.status == SubscriptionStatus.ACTIVE,
            )
            .first()
        )
        plan = db.get(Plan, sub.plan_id) if sub else None
        ledger = (
            db.query(CreditLedger)
            .filter(CreditLedger.user_id == user_id)
            .order_by(CreditLedger.fecha.desc())
            .limit(20)
            .all()
        )
        return CreditsBalance(
            user_id=user_id,
            balance=self.balance(db, user_id),
            plan=PlanRead.model_validate(plan) if plan else None,
            ledger=ledger,
        )
