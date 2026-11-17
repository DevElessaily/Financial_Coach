from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.notification import Notification
from app.schemas.Notification import DeviceTokenCreate, NotificationCreate, NotificationResponse
from app.services.notifications.notificationservice import NotificationService

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


class ReadUpdate(BaseModel):
    is_read: bool = True


@router.get("", response_model=list[NotificationResponse])
def list_notifications(limit: int = 100, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return NotificationService.list_for_user(db, user.id, limit)


@router.post("", response_model=NotificationResponse, status_code=201)
def create_notification(payload: NotificationCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return NotificationService.create(db, user_id=user.id, title=payload.title, body=payload.body, notification_type=payload.type, data=payload.data)


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(notification_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    item = db.get(Notification, notification_id)
    if item is None or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="Notification not found")
    return NotificationService.mark_read(db, item)


@router.post("/device-token", status_code=201)
def register_device_token(payload: DeviceTokenCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if payload.platform.lower() not in {"android", "ios", "web"}:
        raise HTTPException(status_code=422, detail="platform must be android, ios, or web")
    item = NotificationService.register_device(db, user_id=user.id, token=payload.token.strip(), platform=payload.platform.lower())
    return {"id": item.id, "platform": item.platform, "registered": True}
