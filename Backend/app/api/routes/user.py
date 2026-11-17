
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import GetDb
from app.api.dependencies import GetCurrentUser
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from app.services.user_service import (
    UpdateUser,
)

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get("/me", response_model=UserResponse)
def GetMyProfile(
    CurrentUser: User = Depends(GetCurrentUser),
):
    return CurrentUser


@router.patch("/me", response_model=UserResponse)
def UpdateMyProfile(
    UserData: UserUpdate,
    Db: Session = Depends(GetDb),
    CurrentUser: User = Depends(GetCurrentUser),
):
    return UpdateUser(Db, CurrentUser, UserData)
