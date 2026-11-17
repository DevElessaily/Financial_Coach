from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.sms_regular_exp import SMSRegularExp
from app.models.sms_sender import SMSSender
from app.schemas.sms_regular_exp import SMSRegularExpCreate, SMSRegularExpUpdate
from app.services.sms_regular_exp_service import SMSRegularExpService

router = APIRouter(prefix="/api/sms-regex", tags=["SMS Regex"])


def _response(item: SMSRegularExp) -> dict:
    return {
        "id": item.id,
        "sender_id": item.sender_id,
        "transaction_type": item.transaction_type,
        "regular_exp": item.regular_exp,
        "data": item.data,
        "is_active": item.is_active,
        "is_valid_transaction": item.is_valid_transaction,
        "is_valid_regular_exp": item.is_valid_regular_exp,
    }


@router.get("")
def list_regexes(sender_id: int | None = None, db: Session = Depends(get_db)):
    return [_response(item) for item in SMSRegularExpService.list_regexes(db, sender_id)]


@router.post("", status_code=201)
def create_regex(payload: SMSRegularExpCreate, db: Session = Depends(get_db)):
    if db.get(SMSSender, payload.sender_id) is None:
        raise HTTPException(status_code=404, detail="Sender not found")
    try:
        return _response(SMSRegularExpService.store_regex(db, payload))
    except Exception as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/match")
def match_regex(sender_id: int, message: str, db: Session = Depends(get_db)):
    return {
        "valid": SMSRegularExpService.find_valid_regex(db, sender_id, message),
        "invalid": SMSRegularExpService.find_invalid_regex(db, sender_id, message),
    }


@router.patch("/{expression_id}")
def update_regex(expression_id: int, payload: SMSRegularExpUpdate, db: Session = Depends(get_db)):
    item = SMSRegularExpService.get_regex(db, expression_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Expression not found")
    if payload.sender_id is not None and db.get(SMSSender, payload.sender_id) is None:
        raise HTTPException(status_code=404, detail="Sender not found")
    try:
        return _response(SMSRegularExpService.update_regex(db, item, payload))
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.delete("/{expression_id}")
def delete_regex(expression_id: int, db: Session = Depends(get_db)):
    item = SMSRegularExpService.get_regex(db, expression_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Expression not found")
    SMSRegularExpService.delete_regex(db, item)
    return {"status": "deleted", "id": expression_id}
