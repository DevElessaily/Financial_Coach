
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.category import Category


class CategoryService:

    @staticmethod
    def GetTranslationMap(
        Db: Session,
        Locale: str = "en"
    ) -> dict[str, str]:

        Categories = Db.scalars(
            select(Category).order_by(Category.Name)
        ).all()

        return {
            CategoryRecord.Name: CategoryRecord.TranslatedName(
                Locale
            )
            for CategoryRecord in Categories
        }

    @staticmethod
    def GetCategories(
        Db: Session,
        Locale: str = "en"
    ) -> list[dict]:

        Categories = Db.scalars(
            select(Category).order_by(Category.Name)
        ).all()

        return [
            {
                "Id": CategoryRecord.Id,
                "Name": CategoryRecord.Name,
                "TranslatedName": CategoryRecord.TranslatedName(
                    Locale
                ),
                "EnablePrompt": CategoryRecord.EnablePrompt
            }
            for CategoryRecord in Categories
        ]

    @staticmethod
    def CreateCategory(
        Db: Session,
        Name: str,
        Translations: dict | None = None,
        CategoryPrompt: str | None = None,
        EnablePrompt: bool = False
    ) -> Category:

        CleanName = Name.strip()

        if not CleanName:
            raise ValueError("Category name cannot be empty")

        ExistingCategory = Db.scalar(
            select(Category).where(
                func.lower(Category.Name) == CleanName.lower()
            )
        )

        if ExistingCategory:
            raise ValueError("Category already exists")

        NewCategory = Category(
            Name=CleanName,
            Translations=Translations,
            CategoryPrompt=CategoryPrompt,
            EnablePrompt=EnablePrompt
        )

        Db.add(NewCategory)
        Db.commit()
        Db.refresh(NewCategory)

        return NewCategory
