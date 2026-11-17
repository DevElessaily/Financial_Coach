from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.alert import Alert
from app.schemas.alert import AlertCreate, AlertResponse
from app.services.alert_service import AlertService

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])


@router.get("", response_model=list[AlertResponse])
def list_alerts(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return AlertService.list_for_user(db, user.id)


@router.post("", response_model=AlertResponse, status_code=201)
def create_alert(payload: AlertCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        return AlertService.create(db, user_id=user.id, name=payload.name, direction=payload.direction, threshold=payload.threshold, currency_code=payload.currency_code)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.delete("/{alert_id}")
def delete_alert(alert_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    alert = db.get(Alert, alert_id)
    if alert is None or alert.user_id != user.id:
        raise HTTPException(status_code=404, detail="Alert not found")
    AlertService.delete(db, alert)
    return {"status": "deleted", "id": alert_id}
