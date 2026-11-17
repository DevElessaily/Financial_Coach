
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import GetDb
from app.services.category_mapping_service import (
    CategoryMappingService
)


Router = APIRouter(
    prefix="/category-mappings",
    tags=["Category Mappings"]
)


class CategoryMappingCreate(BaseModel):
    AccountName: str
    CategoryName: str


@Router.get("/lookup")
def LookupCategory(
    AccountName: str,
    Db: Session = Depends(GetDb)
):
    Mapping = CategoryMappingService.LookupMapping(
        Db,
        AccountName
    )

    if Mapping is None:
        return {
            "Found": False,
            "CategoryName": None,
            "AlternativeCategoryIds": []
        }

    return {
        "Found": True,
        "CategoryName": (
            Mapping.Category.Name
            if Mapping.Category
            else None
        ),
        "AlternativeCategoryIds": (
            Mapping.AlternativeCategoryIds or []
        )
    }


@Router.post("/")
def SaveCategoryMapping(
    Data: CategoryMappingCreate,
    Db: Session = Depends(GetDb)
):
    Mapping = CategoryMappingService.StoreMapping(
        Db,
        Data.AccountName,
        Data.CategoryName
    )

    if Mapping is None:
        raise HTTPException(
            status_code=400,
            detail="Account name and category name are required"
        )

    return {
        "Message": "Category mapping saved",
        "AccountName": Mapping.AccountName,
        "CategoryId": Mapping.CategoryId
    }
