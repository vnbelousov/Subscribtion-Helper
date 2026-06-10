from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from data_access_module.models import Category


DEFAULT_CATEGORIES = [
    ("Развлечения", "🎬"),
    ("Образование", "📚"),
    ("Работа", "💼"),
    ("Здоровье и фитнес", "🏃"),
    ("Другое", "📦"),
]


async def create_default_categories(session: AsyncSession) -> None:
    result = await session.execute(select(Category))
    existing_categories = result.scalars().all()

    if existing_categories:
        return

    for name, icon in DEFAULT_CATEGORIES:
        category = Category(name=name, icon=icon)
        session.add(category)

    await session.commit()


async def get_all_categories(session: AsyncSession) -> list[Category]:
    result = await session.execute(
        select(Category).order_by(Category.id)
    )

    return list(result.scalars().all())


async def get_category_by_id(
    session: AsyncSession,
    category_id: int,
) -> Category | None:
    result = await session.execute(
        select(Category).where(Category.id == category_id)
    )

    return result.scalar_one_or_none()