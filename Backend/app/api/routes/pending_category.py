
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import get_current_user

from app.models.category import Category
from app.models.transaction import Transaction
from app.models.pending_category_review import PendingCategoryReview

from app.schemas.pending_category_review import (
    ApproveCategoryRequest,
    CategoryOption,
    PendingCategoryReviewResponse,
    ReviewActionResponse,
)

router = APIRouter(
    prefix="/api/pending-category-reviews",
    tags=["Pending Category Reviews"],
)


def get_visible_review(
    db: Session,
    review_id: int,
    user,
) -> PendingCategoryReview:
    query = select(PendingCategoryReview).where(
        PendingCategoryReview.id == review_id
    )

    # Users can access their own reviews and reviews shared
    # with their budget.
    conditions = [
        PendingCategoryReview.user_id == user.id
    ]

    if getattr(user, "budget_id", None):
        conditions.append(
            PendingCategoryReview.budget_id == user.budget_id
        )

    query = query.where(or_(*conditions))
    review = db.scalar(query)

    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category review not found",
        )

    return review


def build_review_response(
    db: Session,
    review: PendingCategoryReview,
) -> PendingCategoryReviewResponse:
    current_category = None

    if review.current_category_id is not None:
        current_category = db.get(
            Category,
            review.current_category_id,
        )

    alternative_ids = review.alternative_category_ids or []
    alternative_categories = []

    if alternative_ids:
        categories = db.scalars(
            select(Category).where(
                Category.Id.in_(alternative_ids)
            )
        ).all()

        # Preserve the order of IDs supplied by the review.
        categories_by_id = {
            category.Id: category for category in categories
        }

        alternative_categories = [
            categories_by_id[category_id]
            for category_id in alternative_ids
            if category_id in categories_by_id
        ]

    return PendingCategoryReviewResponse(
        id=review.id,
        transaction_id=review.transaction_id,
        account_name=review.account_name,
        current_category_id=review.current_category_id,
        current_category=(
            CategoryOption(
                id=current_category.Id,
                name=current_category.Name,
                translated_name=current_category.TranslatedName("en"),
                enable_prompt=current_category.EnablePrompt,
            )
            if current_category else None
        ),
        alternative_category_ids=alternative_ids,
        alternative_categories=[
            CategoryOption(
                id=category.Id,
                name=category.Name,
                translated_name=category.TranslatedName("en"),
                enable_prompt=category.EnablePrompt,
            )
            for category in alternative_categories
        ],
        transaction_amount=review.transaction_amount,
        currency_code=review.currency_code,
        transaction_date=review.transaction_date,
        transaction_description=review.transaction_description,
        status=review.status,
    )


@router.get("", response_model=list[PendingCategoryReviewResponse])
def get_pending_reviews(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    conditions = [
        PendingCategoryReview.user_id == current_user.id
    ]

    if getattr(current_user, "budget_id", None):
        conditions.append(
            PendingCategoryReview.budget_id == current_user.budget_id
        )

    query = (
        select(PendingCategoryReview)
        .where(
            PendingCategoryReview.status == "pending",
            or_(*conditions),
        )
        .order_by(PendingCategoryReview.id.desc())
    )

    reviews = db.scalars(query).all()

    return [
        build_review_response(db, review)
        for review in reviews
    ]


@router.get(
    "/{review_id}",
    response_model=PendingCategoryReviewResponse,
)
def get_pending_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    review = get_visible_review(db, review_id, current_user)

    return build_review_response(db, review)


@router.post(
    "/{review_id}/approve",
    response_model=ReviewActionResponse,
)
def approve_category_review(
    review_id: int,
    request: ApproveCategoryRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    review = get_visible_review(db, review_id, current_user)

    if review.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This review has already been processed",
        )

    category = db.get(Category, request.category_id)

    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Selected category not found",
        )

    if review.transaction_id is not None:
        transaction = db.get(Transaction, review.transaction_id)

        if transaction is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The associated transaction was not found",
            )

        # Assumes Transaction has a category_id column.
        transaction.CategoryId = category.Id

    review.current_category_id = category.id
    review.status = "approved"

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return ReviewActionResponse(
        message="Category approved successfully",
        review_id=review.id,
        status=review.status,
        selected_category_id=category.id,
    )


@router.post(
    "/{review_id}/reject",
    response_model=ReviewActionResponse,
)
def reject_category_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    review = get_visible_review(db, review_id, current_user)

    if review.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This review has already been processed",
        )

    review.status = "rejected"

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return ReviewActionResponse(
        message="Category review rejected",
        review_id=review.id,
        status=review.status,
    )
