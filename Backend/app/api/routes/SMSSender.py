# app/routes/sms_senders.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.schemas.sms_sender import (
    SMSSenderCreate,
    SMSSenderUpdate,
    SMSSenderResponse,
    SMSSenderValidationResponse,
)
from app.services.sms_sender_service import SMSSenderService


router = APIRouter(
    prefix="/api/sms-senders",
    tags=["SMS Senders"],
)


@router.post("/", response_model=SMSSenderResponse, status_code=201)
def create_sender(
    data: SMSSenderCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        return SMSSenderService.create_sender(db, data)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))


@router.get("/", response_model=list[SMSSenderResponse])
def get_senders(
    active_only: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return SMSSenderService.get_senders(db, active_only)


@router.get(
    "/validate/{sender}",
    response_model=SMSSenderValidationResponse,
)
def validate_sender(
    sender: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return SMSSenderValidationResponse(
        sender=sender,
        is_valid=SMSSenderService.is_valid_sender(db, sender),
    )


@router.get("/{sender_id}", response_model=SMSSenderResponse)
def get_sender(
    sender_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    sender = SMSSenderService.get_sender(db, sender_id)

    if sender is None:
        raise HTTPException(status_code=404, detail="SMS sender not found.")

    return sender


@router.patch("/{sender_id}", response_model=SMSSenderResponse)
def update_sender(
    sender_id: int,
    data: SMSSenderUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        sender = SMSSenderService.update_sender(db, sender_id, data)

        if sender is None:
            raise HTTPException(
                status_code=404,
                detail="SMS sender not found.",
            )

        return sender

    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))


@router.delete("/{sender_id}")
def delete_sender(
    sender_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    deleted = SMSSenderService.delete_sender(db, sender_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="SMS sender not found.")

    return {"message": "SMS sender deleted successfully."}