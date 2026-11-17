from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.pending_category_review import PendingCategoryReview


class PendingCategoryService:
    @staticmethod
    def list_pending(db: Session, user_id: int, budget_id: int | None = None) -> list[PendingCategoryReview]:
        visibility = [PendingCategoryReview.user_id == user_id]
        if budget_id is not None:
            visibility.append(PendingCategoryReview.budget_id == budget_id)
        return list(db.scalars(select(PendingCategoryReview).where(
            PendingCategoryReview.status == "pending", or_(*visibility)
        ).order_by(PendingCategoryReview.id.desc())).all())

    @staticmethod
    def resolve(db: Session, review: PendingCategoryReview, status: str) -> PendingCategoryReview:
        if status not in {"approved", "rejected"}:
            raise ValueError("status must be approved or rejected")
        review.status = status
        db.commit()
        db.refresh(review)
        return review
