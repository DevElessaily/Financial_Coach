from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.models.sms_sender import SMSSender
from app.models.account import Account
from app.schemas.sms_sender import SMSSenderCreate, SMSSenderResponse
from app.services.sms_sender_service import SMSSenderService

router = APIRouter(prefix="/api/sms-senders", tags=["SMS Senders"])


@router.get("", response_model=list[SMSSenderResponse])
def list_senders(db: Session = Depends(get_db)):
    return SMSSenderService.list(db)


@router.post("", response_model=SMSSenderResponse, status_code=201)
def create_sender(payload: SMSSenderCreate, db: Session = Depends(get_db)):
    try:
        return SMSSenderService.create(db, payload.name)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.delete("/{sender_id}")
def delete_sender(sender_id: int, db: Session = Depends(get_db)):
    sender = SMSSenderService.get(db, sender_id)
    if sender is None:
        raise HTTPException(status_code=404, detail="Sender not found")
    if sender.regular_expressions or db.scalar(select(Account.Id).where(Account.SenderId == sender_id).limit(1)):
        raise HTTPException(status_code=409, detail="Delete the sender's expressions first")
    SMSSenderService.delete(db, sender)
    return {"status": "deleted", "id": sender_id}
