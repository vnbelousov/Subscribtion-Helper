from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from data_access_module.database import async_session
from command_module.keyboards import get_main_menu
from subscription_module.user_service import get_or_create_user

router = Router()

@router.message(CommandStart())
async def start_command(message: Message) -> None:
    async with async_session() as session:
        await get_or_create_user(session, message.from_user)

    await message.answer(
        "Привет! Я помогу тебе отслеживать подписки, напоминать о платежах "
        "и считать расходы.\n\n"
        "Выбери действие в меню ниже.",
        reply_markup=get_main_menu(),
    )