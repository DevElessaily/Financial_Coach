from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.models.category import Category
from app.models.transaction import Transaction
from app.services.category_service import CategoryService

router = APIRouter(prefix="/api/categories", tags=["Categories"])


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    translations: dict[str, str] | None = None


@router.get("")
def list_categories(db: Session = Depends(get_db)):
    return CategoryService.GetCategories(db)


@router.post("", status_code=201)
def create_category(payload: CategoryCreate, db: Session = Depends(get_db)):
    try:
        category = CategoryService.CreateCategory(
            db, payload.name, Translations=payload.translations
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return {"id": category.Id, "name": category.Name}


@router.delete("/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db)):
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    if db.scalar(select(Transaction.Id).where(Transaction.CategoryId == category_id).limit(1)):
        raise HTTPException(status_code=409, detail="Category is used by transactions")
    db.delete(category)
    db.commit()
    return {"status": "deleted", "id": category_id}
