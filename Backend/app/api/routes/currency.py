from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.currency import Currency
from app.schemas.currency import CurrencyConversionRequest, CurrencyConversionResponse, CurrencyResponse, CurrencyUpsert
from app.services.currency_service import CurrencyService

router = APIRouter(prefix="/api/currency", tags=["Currency"])


@router.get("", response_model=list[CurrencyResponse])
def list_currencies(db: Session = Depends(get_db)):
    return CurrencyService.list_supported(db)


@router.put("/{code}", response_model=CurrencyResponse)
def put_currency(code: str, payload: CurrencyUpsert, db: Session = Depends(get_db)):
    if code.upper() != payload.code.upper():
        raise HTTPException(status_code=422, detail="Path code must match payload code")
    try:
        return CurrencyService.upsert(db, payload.code, payload.name, payload.symbol)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.delete("/{code}")
def delete_currency(code: str, db: Session = Depends(get_db)):
    item = db.get(Currency, code.upper())
    if item is None or not item.is_active:
        raise HTTPException(status_code=404, detail="Currency not found")
    CurrencyService.delete(db, item)
    return {"status": "deactivated", "code": item.code}


@router.post("/convert", response_model=CurrencyConversionResponse)
def convert_currency(payload: CurrencyConversionRequest):
    rate = CurrencyService.exchange_rate(1, payload.from_currency, payload.to_currency)
    if rate is None:
        raise HTTPException(status_code=422, detail="Exchange rate unavailable for this currency pair")
    converted = CurrencyService.exchange_rate(payload.amount, payload.from_currency, payload.to_currency)
    if converted is None:
        raise HTTPException(status_code=422, detail="Currency conversion failed")
    return CurrencyConversionResponse(
        amount=payload.amount,
        from_currency=payload.from_currency.upper(),
        to_currency=payload.to_currency.upper(),
        exchange_rate=rate,
        converted_amount=converted,
    )
