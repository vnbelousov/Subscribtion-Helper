import asyncio

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

import data_access_module.models
from config import load_config
from data_access_module.database import async_session, create_tables
from command_module.start_handler import router as start_router
from command_module.subscription_handler import router as subscriptions_router
from subscription_module.category_service import create_default_categories
from notification_module.reminder_service import check_and_send_reminders
from subscription_module.subscription_service import update_overdue_payment_dates


async def reminders_worker(bot: Bot) -> None:
    while True:
        async with async_session() as session:
            await update_overdue_payment_dates(session)
            await check_and_send_reminders(bot, session)

        await asyncio.sleep(60)


async def main() -> None:
    config = load_config()

    await create_tables()

    async with async_session() as session:
        await create_default_categories(session)

    bot = Bot(token=config.bot_token)
    dispatcher = Dispatcher(storage=MemoryStorage())

    dispatcher.include_router(start_router)
    dispatcher.include_router(subscriptions_router)

    asyncio.create_task(reminders_worker(bot))

    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())