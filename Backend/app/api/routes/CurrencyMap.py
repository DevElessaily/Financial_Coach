
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.currency_map import CurrencyMap
from app.schemas.currency_map import (
    CurrencyMapCreate,
    CurrencyMapResponse,
    CurrencyResolveRequest,
    CurrencyResolveResponse,
)
from app.services.currency_map_service import CurrencyMapService


router = APIRouter(
    prefix="/api/currencies",
    tags=["Currencies"]
)


@router.get("/lookup/{text}")
def lookup_currency(
    text: str,
    db: Session = Depends(get_db)
):
    code = CurrencyMapService.lookup(text, db)

    if code is None:
        raise HTTPException(
            status_code=404,
            detail="Currency not found"
        )

    return {"text": text, "code": code}


@router.post(
    "/resolve",
    response_model=CurrencyResolveResponse
)
def resolve_currency(
    request: CurrencyResolveRequest,
    db: Session = Depends(get_db)
):
    code = CurrencyMapService.resolve(
        request.text,
        db
    )

    return CurrencyResolveResponse(
        text=request.text,
        code=code
    )


@router.post(
    "",
    response_model=CurrencyMapResponse,
    status_code=201
)
def create_currency(
    request: CurrencyMapCreate,
    db: Session = Depends(get_db)
):
    code = request.code.strip().upper()

    existing = CurrencyMapService.lookup(code, db)

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Currency already exists"
        )

    currency = CurrencyMap(
        code=code,
        name=request.name.strip(),
        aliases=request.aliases
    )

    db.add(currency)
    db.commit()
    db.refresh(currency)

    return currency


@router.post("/{code}/aliases")
def add_currency_alias(
    code: str,
    alias: str,
    db: Session = Depends(get_db)
):
    success = CurrencyMapService.add_alias(
        code,
        alias,
        db
    )

    if not success:
        raise HTTPException(
            status_code=404,
            detail="Currency not found or alias is empty"
        )

    return {
        "message": "Alias added successfully"
    }
