from datetime import date, datetime, time, timedelta

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from data_access_module.models import Reminder, Subscription, User


def get_reminder_datetime(subscription: Subscription) -> datetime:
    reminder_date = (
        subscription.next_payment_date
        - timedelta(days=subscription.reminder_days_before)
    )

    return datetime.combine(reminder_date, time(hour=9, minute=0))


async def reminder_already_sent(
    session: AsyncSession,
    subscription: Subscription,
    send_at: datetime,
) -> bool:
    result = await session.execute(
        select(Reminder).where(
            Reminder.subscription_id == subscription.id,
            Reminder.send_at == send_at,
            Reminder.status == "sent",
        )
    )

    reminder = result.scalar_one_or_none()

    return reminder is not None


async def save_sent_reminder(
    session: AsyncSession,
    subscription: Subscription,
    send_at: datetime,
) -> None:
    reminder = Reminder(
        subscription_id=subscription.id,
        send_at=send_at,
        status="sent",
    )

    session.add(reminder)
    await session.commit()


async def get_subscriptions_for_reminder(
    session: AsyncSession,
) -> list[Subscription]:
    today = date.today()

    result = await session.execute(
        select(Subscription)
        .options(
            selectinload(Subscription.user),
            selectinload(Subscription.category),
        )
        .where(
            Subscription.status == "active",
            Subscription.reminders_enabled == True,
        )
    )

    subscriptions = list(result.scalars().all())

    result_subscriptions = []

    for subscription in subscriptions:
        reminder_date = (
            subscription.next_payment_date
            - timedelta(days=subscription.reminder_days_before)
        )

        if reminder_date <= today:
            result_subscriptions.append(subscription)

    return result_subscriptions


async def check_and_send_reminders(
    bot: Bot,
    session: AsyncSession,
) -> None:
    subscriptions = await get_subscriptions_for_reminder(session)

    for subscription in subscriptions:
        send_at = get_reminder_datetime(subscription)

        if await reminder_already_sent(session, subscription, send_at):
            continue

        text = (
            "Напоминание о подписке\n\n"
            f"Сервис: {subscription.service_name}\n"
            f"Стоимость: {subscription.price} {subscription.currency}\n"
            f"Дата списания: {subscription.next_payment_date.strftime('%d.%m.%Y')}\n"
            f"Категория: {subscription.category.icon} {subscription.category.name}"
        )

        await bot.send_message(
            chat_id=subscription.user.telegram_id,
            text=text,
        )

        await save_sent_reminder(session, subscription, send_at)