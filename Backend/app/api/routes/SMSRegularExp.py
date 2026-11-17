
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.schemas.sms_regular_exp import (
    SMSRegularExpCreate,
    SMSRegularExpUpdate,
    SMSRegularExpResponse,
    SMSRegularExpMatchResponse,
    SMSRegularExpTestRequest,
    SMSRegularExpTestResponse,
)
from app.services.sms_regular_exp_service import SMSRegularExpService


router = APIRouter(
    prefix="/api/sms-regular-exps",
    tags=["SMS Regular Expressions"],
)


def get_expression_or_404(db: Session, expression_id: int):
    expression = SMSRegularExpService.get_regex(db, expression_id)

    if expression is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Regex pattern not found.",
        )

    return expression


@router.get("", response_model=list[SMSRegularExpResponse])
def list_regexes(
    sender_id: int | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Restrict this endpoint to authorized users in your application.
    return SMSRegularExpService.list_regexes(db, sender_id)


@router.get(
    "/{expression_id}",
    response_model=SMSRegularExpResponse,
)
def get_regex(
    expression_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return get_expression_or_404(db, expression_id)


@router.post(
    "",
    response_model=SMSRegularExpResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_regex(
    data: SMSRegularExpCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        return SMSRegularExpService.store_regex(db, data)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not save the regex pattern.",
        )


@router.patch(
    "/{expression_id}",
    response_model=SMSRegularExpResponse,
)
def update_regex(
    expression_id: int,
    data: SMSRegularExpUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    expression = get_expression_or_404(db, expression_id)

    try:
        return SMSRegularExpService.update_regex(db, expression, data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )


@router.delete(
    "/{expression_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_regex(
    expression_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    expression = get_expression_or_404(db, expression_id)
    SMSRegularExpService.delete_regex(db, expression)
    return None


@router.post("/test", response_model=SMSRegularExpTestResponse)
def test_regex(
    data: SMSRegularExpTestRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = SMSRegularExpService.find_regex(
        db=db,
        sender_id=data.sender_id,
        message=data.message,
        is_valid_regular_exp=True,
        is_valid_transaction=data.is_valid_transaction,
    )

    if result is None:
        return SMSRegularExpTestResponse(matched=False)

    return SMSRegularExpTestResponse(
        matched=True,
        result=SMSRegularExpMatchResponse(**result),
    )
