from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.currency_map import CurrencyMap
from app.schemas.currency_map import CurrencyMapResponse, CurrencyMapUpsert
from app.services.currency_map_service import CurrencyMapService

router = APIRouter(prefix="/api/currency-maps", tags=["Currency Maps"])


@router.get("", response_model=list[CurrencyMapResponse])
def list_currency_maps(db: Session = Depends(get_db)):
    return CurrencyMapService.list_all(db)


@router.put("/{code}", response_model=CurrencyMapResponse)
def put_currency_map(code: str, payload: CurrencyMapUpsert, db: Session = Depends(get_db)):
    if code.upper() != payload.code.upper():
        raise HTTPException(status_code=422, detail="Path code must match payload code")
    try:
        return CurrencyMapService.upsert(db, payload.code, payload.name, payload.aliases)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.delete("/{code}")
def delete_currency_map(code: str, db: Session = Depends(get_db)):
    item = CurrencyMapService.get(db, code)
    if item is None:
        raise HTTPException(status_code=404, detail="Currency map not found")
    CurrencyMapService.delete(db, item)
    return {"status": "deleted", "code": code.upper()}
