from aiogram.types import User as TelegramUser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from data_access_module.models import User

async def get_or_create_user(
    session: AsyncSession,
    telegram_user: TelegramUser,
) -> User:
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_user.id)
    )

    user = result.scalar_one_or_none()

    if user:
        return user

    user = User(
        telegram_id=telegram_user.id,
        username=telegram_user.username,
    )

    session.add(user)
    await session.commit()
    await session.refresh(user)

    return user