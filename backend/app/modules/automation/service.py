"""Flags de automatización post-proceso."""

from sqlalchemy.orm import Session

from app.models.saas import AutomationSettings
from app.modules.automation.schemas import AutomationSettingsUpdate
from app.modules.deps import DEFAULT_USER_ID


class AutomationService:
    """Lee/actualiza opciones de automatización."""

    def get_or_create(self, db: Session, user_id: int = DEFAULT_USER_ID) -> AutomationSettings:
        row = (
            db.query(AutomationSettings)
            .filter(AutomationSettings.user_id == user_id)
            .first()
        )
        if not row:
            row = AutomationSettings(
                user_id=user_id,
                enrich_after_process=True,
                auto_schedule_stubs=False,
                auto_thumbnails=True,
                default_platforms=["tiktok", "shorts"],
            )
            db.add(row)
            db.commit()
            db.refresh(row)
        return row

    def update(
        self, db: Session, user_id: int, body: AutomationSettingsUpdate
    ) -> AutomationSettings:
        row = self.get_or_create(db, user_id)
        data = body.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(row, k, v)
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
