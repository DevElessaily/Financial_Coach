from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.models.category_mapping import CategoryMapping
from app.models.pending_category_review import PendingCategoryReview
from app.services.category_mapping_service import CategoryMappingService

router = APIRouter(prefix="/api/category-mappings", tags=["Category Mappings"])


class MappingCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


@router.get("")
def list_mappings(db: Session = Depends(get_db)):
    return [{"id": item.Id, "name": item.Name} for item in CategoryMappingService.list(db)]


@router.post("", status_code=201)
def create_mapping(payload: MappingCreate, db: Session = Depends(get_db)):
    try:
        item = CategoryMappingService.create(db, payload.name)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return {"id": item.Id, "name": item.Name}


@router.delete("/{mapping_id}")
def delete_mapping(mapping_id: int, db: Session = Depends(get_db)):
    item = db.get(CategoryMapping, mapping_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Mapping not found")
    if db.scalar(select(PendingCategoryReview.id).where(PendingCategoryReview.category_mapping_id == mapping_id).limit(1)):
        raise HTTPException(status_code=409, detail="Mapping is used by a pending category review")
    CategoryMappingService.delete(db, item)
    return {"status": "deleted", "id": mapping_id}
