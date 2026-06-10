from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from data_access_module.models import Subscription, User
from utils.date_utils import calculate_next_payment_date


async def create_subscription(
    session: AsyncSession,
    user: User,
    category_id: int,
    service_name: str,
    price: Decimal,
    billing_period: str,
    next_payment_date: date,
) -> Subscription:
    subscription = Subscription(
        user_id=user.id,
        category_id=category_id,
        service_name=service_name,
        price=price,
        currency="RUB",
        billing_period=billing_period,
        start_date=date.today(),
        next_payment_date=next_payment_date,
        status="active",
        reminders_enabled=True,
        reminder_days_before=1,
    )

    session.add(subscription)
    await session.commit()
    await session.refresh(subscription)

    return subscription


async def get_active_subscriptions_by_user(
    session: AsyncSession,
    user: User,
) -> list[Subscription]:
    result = await session.execute(
        select(Subscription)
        .options(selectinload(Subscription.category))
        .where(
            Subscription.user_id == user.id,
            Subscription.status == "active",
        )
        .order_by(Subscription.next_payment_date)
    )

    return list(result.scalars().all())

async def get_subscription_by_id(
    session: AsyncSession,
    subscription_id: int,
    user: User,
) -> Subscription | None:
    result = await session.execute(
        select(Subscription)
        .options(selectinload(Subscription.category))
        .where(
            Subscription.id == subscription_id,
            Subscription.user_id == user.id,
        )
    )

    return result.scalar_one_or_none()


async def archive_subscription(
    session: AsyncSession,
    subscription: Subscription,
) -> None:
    subscription.status = "archived"
    subscription.reminders_enabled = False

    await session.commit()

async def toggle_subscription_reminders(
    session: AsyncSession,
    subscription: Subscription,
) -> Subscription:
    subscription.reminders_enabled = not subscription.reminders_enabled

    await session.commit()
    await session.refresh(subscription)

    return subscription

async def update_overdue_payment_dates(
    session: AsyncSession,
) -> int:
    today = date.today()

    result = await session.execute(
        select(Subscription).where(
            Subscription.status == "active",
            Subscription.next_payment_date < today,
        )
    )

    subscriptions = list(result.scalars().all())

    updated_count = 0

    for subscription in subscriptions:
        while subscription.next_payment_date < today:
            subscription.next_payment_date = calculate_next_payment_date(
                subscription.next_payment_date,
                subscription.billing_period,
            )

        updated_count += 1

    await session.commit()

    return updated_count

async def update_subscription_service_name(
    session: AsyncSession,
    subscription: Subscription,
    service_name: str,
) -> Subscription:
    subscription.service_name = service_name

    await session.commit()
    await session.refresh(subscription)

    return subscription


async def update_subscription_price(
    session: AsyncSession,
    subscription: Subscription,
    price: Decimal,
) -> Subscription:
    subscription.price = price

    await session.commit()
    await session.refresh(subscription)

    return subscription


async def update_subscription_next_payment_date(
    session: AsyncSession,
    subscription: Subscription,
    next_payment_date: date,
) -> Subscription:
    subscription.next_payment_date = next_payment_date

    await session.commit()
    await session.refresh(subscription)

    return subscription


async def update_subscription_category(
    session: AsyncSession,
    subscription: Subscription,
    category_id: int,
) -> Subscription:
    subscription.category_id = category_id

    await session.commit()
    await session.refresh(subscription)

    return subscription

async def disable_all_reminders_by_user(
    session: AsyncSession,
    user: User,
) -> int:
    result = await session.execute(
        select(Subscription).where(
            Subscription.user_id == user.id,
            Subscription.status == "active",
            Subscription.reminders_enabled == True,
        )
    )

    subscriptions = list(result.scalars().all())

    for subscription in subscriptions:
        subscription.reminders_enabled = False

    await session.commit()

    return len(subscriptions)


async def enable_all_reminders_by_user(
    session: AsyncSession,
    user: User,
) -> int:
    result = await session.execute(
        select(Subscription).where(
            Subscription.user_id == user.id,
            Subscription.status == "active",
            Subscription.reminders_enabled == False,
        )
    )

    subscriptions = list(result.scalars().all())

    for subscription in subscriptions:
        subscription.reminders_enabled = True

    await session.commit()

    return len(subscriptions)