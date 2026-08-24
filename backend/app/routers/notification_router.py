from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.models.notification import Notification

router = APIRouter(tags=["Notifications"])


def _identity(
    user_id: int | None,
    user_role: str | None,
):
    if not user_id or not user_role:
        raise HTTPException(
            status_code=401,
            detail="Authenticated user context is required.",
        )
    return user_id, user_role


@router.get("/notifications")
def list_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(30, ge=1, le=100),
    user_id: int | None = Header(default=None, alias="X-User-Id"),
    user_role: str | None = Header(default=None, alias="X-User-Role"),
    db: Session = Depends(get_db),
):
    user_id, user_role = _identity(user_id, user_role)

    query = (
        db.query(Notification)
        .filter(
            Notification.recipient_id == user_id,
            Notification.recipient_role == user_role,
        )
    )

    if unread_only:
        query = query.filter(
            Notification.is_read.is_(False)
        )

    return (
        query
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/notifications/unread-count")
def unread_count(
    user_id: int | None = Header(default=None, alias="X-User-Id"),
    user_role: str | None = Header(default=None, alias="X-User-Role"),
    db: Session = Depends(get_db),
):
    user_id, user_role = _identity(user_id, user_role)

    count = (
        db.query(Notification)
        .filter(
            Notification.recipient_id == user_id,
            Notification.recipient_role == user_role,
            Notification.is_read.is_(False),
        )
        .count()
    )

    return {"unread_count": count}


@router.patch("/notifications/{notification_id}/read")
def mark_read(
    notification_id: int,
    user_id: int | None = Header(default=None, alias="X-User-Id"),
    user_role: str | None = Header(default=None, alias="X-User-Role"),
    db: Session = Depends(get_db),
):
    user_id, user_role = _identity(user_id, user_role)

    notification = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.recipient_id == user_id,
            Notification.recipient_role == user_role,
        )
        .first()
    )

    if not notification:
        raise HTTPException(
            status_code=404,
            detail="Notification not found.",
        )

    notification.is_read = True
    notification.read_at = datetime.utcnow()

    db.commit()
    db.refresh(notification)

    return notification


@router.post("/notifications/read-all")
def mark_all_read(
    user_id: int | None = Header(default=None, alias="X-User-Id"),
    user_role: str | None = Header(default=None, alias="X-User-Role"),
    db: Session = Depends(get_db),
):
    user_id, user_role = _identity(user_id, user_role)

    now = datetime.utcnow()

    updated = (
        db.query(Notification)
        .filter(
            Notification.recipient_id == user_id,
            Notification.recipient_role == user_role,
            Notification.is_read.is_(False),
        )
        .update(
            {
                Notification.is_read: True,
                Notification.read_at: now,
            },
            synchronize_session=False,
        )
    )

    db.commit()

    return {"updated": updated}
