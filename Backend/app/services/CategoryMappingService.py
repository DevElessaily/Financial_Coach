
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.category_mapping import CategoryMapping


class CategoryMappingService:

    @staticmethod
    def Lookup(
        Db: Session,
        AccountName: str
    ) -> str | None:

        Mapping = CategoryMappingService.LookupMapping(
            Db,
            AccountName
        )

        if Mapping is None or Mapping.Category is None:
            return None

        return Mapping.Category.Name

    @staticmethod
    def LookupMapping(
        Db: Session,
        AccountName: str
    ) -> CategoryMapping | None:

        CleanName = AccountName.strip()

        if not CleanName:
            return None

        return Db.scalar(
            select(CategoryMapping).where(
                func.lower(CategoryMapping.AccountName)
                == CleanName.lower()
            )
        )

    @staticmethod
    def StoreMapping(
        Db: Session,
        AccountName: str,
        CategoryName: str
    ) -> CategoryMapping | None:

        CleanAccountName = AccountName.strip()
        CleanCategoryName = CategoryName.strip()

        if not CleanAccountName or not CleanCategoryName:
            return None

        try:
            # Find the category without case sensitivity.
            CategoryRecord = Db.scalar(
                select(Category).where(
                    func.lower(Category.Name)
                    == CleanCategoryName.lower()
                )
            )

            # Create the category if it doesn't exist.
            if CategoryRecord is None:
                CategoryRecord = Category(
                    Name=CleanCategoryName
                )

                Db.add(CategoryRecord)
                Db.flush()

            # Find the existing merchant mapping.
            Mapping = Db.scalar(
                select(CategoryMapping).where(
                    func.lower(CategoryMapping.AccountName)
                    == CleanAccountName.lower()
                )
            )

            if Mapping is None:
                Mapping = CategoryMapping(
                    AccountName=CleanAccountName,
                    CategoryId=CategoryRecord.Id,
                    AlternativeCategoryIds=[]
                )

                Db.add(Mapping)
            else:
                Mapping.CategoryId = CategoryRecord.Id

            Db.commit()
            Db.refresh(Mapping)

            return Mapping

        except Exception:
            Db.rollback()
            raise
