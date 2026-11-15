import uuid
from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import AuthContext, get_auth_context
from app.modules.users.schemas import (
    UserProfileResponse,
    UserProfileUpdateRequest,
    UserSearchResult,
)
from app.modules.users.services import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(
    auth: AuthContext = Depends(get_auth_context),
):
    return UserProfileResponse.model_validate(auth.user)


@router.patch("/me", response_model=UserProfileResponse)
async def update_my_profile(
    req: UserProfileUpdateRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
):
    user = await UserService.update_profile(db, auth.user.id, req)
    return UserProfileResponse.model_validate(user)


@router.get("/search", response_model=List[UserSearchResult])
async def search_users(
    q: str = Query(..., min_length=2, max_length=50),
    limit: int = Query(20, ge=1, le=50),
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
):
    return await UserService.search_users(db, query=q, limit=limit)


@router.get("/{user_id}", response_model=UserProfileResponse)
async def get_user_profile(
    user_id: uuid.UUID,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
):
    user = await UserService.get_user(db, user_id)
    return UserProfileResponse.model_validate(user)
