from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.sms import SMSParseRequest
from app.services.sms_transaction_parser import parse_transaction_sms
from app.services.sms_service import SMSService

router = APIRouter(prefix="/api/sms", tags=["SMS"])


@router.post("/parse")
def parse_sms(payload: SMSParseRequest):
    transaction = parse_transaction_sms(payload.sender, payload.message)
    if transaction is None:
        return {"is_transaction": False, "transaction": None}
    return {
        "is_transaction": True,
        "transaction": {
            "amount": str(transaction.amount),
            "currency": transaction.currency,
            "type": transaction.db_type,
            "category": transaction.category,
            "description": transaction.description,
            "merchant": transaction.merchant,
            "confidence": transaction.confidence,
        },
    }


@router.post("/process-stored")
def process_stored_sms(limit: int = 5000, db: Session = Depends(get_db)):
    counts = SMSService.process_unlinked(db, limit)
    return {"scanned": sum(counts.values()), "transactions_created": counts["created"], **counts}
