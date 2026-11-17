from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.category_mapping import CategoryMapping


class CategoryMappingService:
    @staticmethod
    def list(db: Session) -> list[CategoryMapping]:
        return list(db.scalars(select(CategoryMapping).order_by(CategoryMapping.Name)).all())

    @staticmethod
    def create(db: Session, name: str) -> CategoryMapping:
        clean = name.strip()
        if not clean:
            raise ValueError("Name cannot be empty")
        if db.scalar(select(CategoryMapping).where(func.lower(CategoryMapping.Name) == clean.lower())):
            raise ValueError("Category mapping already exists")
        item = CategoryMapping(Name=clean)
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def delete(db: Session, item: CategoryMapping) -> None:
        db.delete(item)
        db.commit()
