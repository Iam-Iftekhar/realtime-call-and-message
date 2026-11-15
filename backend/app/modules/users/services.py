import uuid
from typing import List
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.modules.auth.models import User
from app.modules.users.schemas import UserProfileUpdateRequest, UserSearchResult


class UserService:
    @staticmethod
    async def get_user(db: AsyncSession, user_id: uuid.UUID) -> User:
        res = await db.execute(select(User).where(User.id == user_id))
        user = res.scalar_one_or_none()
        if not user:
            raise NotFoundError(detail="User not found", code="USER_NOT_FOUND")
        return user

    @staticmethod
    async def update_profile(
        db: AsyncSession, user_id: uuid.UUID, req: UserProfileUpdateRequest
    ) -> User:
        user = await UserService.get_user(db, user_id)
        if req.display_name is not None:
            user.display_name = req.display_name
        await db.flush()
        return user

    @staticmethod
    async def search_users(db: AsyncSession, query: str, limit: int = 20) -> List[UserSearchResult]:
        search_pattern = f"%{query}%"
        res = await db.execute(
            select(User)
            .where(
                User.status == "active",
                or_(
                    User.username.ilike(search_pattern),
                    User.display_name.ilike(search_pattern),
                ),
            )
            .limit(limit)
        )
        users = res.scalars().all()
        return [
            UserSearchResult(
                id=u.id,
                username=u.username,
                display_name=u.display_name,
            )
            for u in users
        ]
