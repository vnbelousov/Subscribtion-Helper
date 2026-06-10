from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from data_access_module.models import Category


def get_main_menu() -> ReplyKeyboardMarkup:
    keyboard = [
        [
            KeyboardButton(text="➕ Добавить подписку"),
            KeyboardButton(text="📋 Мои подписки"),
        ],
        [
            KeyboardButton(text="📊 Статистика"),
            KeyboardButton(text="⚙️ Настройки"),
        ],
        [
            KeyboardButton(text="❌ Отмена"),
        ],
    ]

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
    )

def get_billing_period_keyboard():
    builder = InlineKeyboardBuilder()

    builder.button(
        text="Ежемесячно",
        callback_data="period:monthly",
    )

    builder.button(
        text="Ежеквартально",
        callback_data="period:quarterly",
    )

    builder.button(
        text="Ежегодно",
        callback_data="period:yearly",
    )

    builder.adjust(1)

    return builder.as_markup()


def get_categories_keyboard(categories: list[Category]):
    builder = InlineKeyboardBuilder()

    for category in categories:
        builder.button(
            text=f"{category.icon} {category.name}",
            callback_data=f"category:{category.id}",
        )

    builder.adjust(1)

    return builder.as_markup()

def get_subscriptions_keyboard(subscriptions):
    builder = InlineKeyboardBuilder()

    for subscription in subscriptions:
        builder.button(
            text=subscription.service_name,
            callback_data=f"subscription:{subscription.id}",
        )

    builder.adjust(1)

    return builder.as_markup()


def get_subscription_actions_keyboard(subscription_id: int, reminders_enabled: bool):
    builder = InlineKeyboardBuilder()

    builder.button(
        text="✏️ Редактировать",
        callback_data=f"edit_subscription:{subscription_id}",
    )

    if reminders_enabled:
        builder.button(
            text="🔕 Отключить напоминания",
            callback_data=f"toggle_reminders:{subscription_id}",
        )
    else:
        builder.button(
            text="🔔 Включить напоминания",
            callback_data=f"toggle_reminders:{subscription_id}",
        )

    builder.button(
        text="🗑 Архивировать",
        callback_data=f"archive_subscription:{subscription_id}",
    )

    builder.button(
        text="⬅️ Назад к списку",
        callback_data="back_to_subscriptions",
    )

    builder.adjust(1)

    return builder.as_markup()

def get_edit_subscription_keyboard(subscription_id: int):
    builder = InlineKeyboardBuilder()

    builder.button(
        text="Название",
        callback_data=f"edit_field:{subscription_id}:service_name",
    )

    builder.button(
        text="Стоимость",
        callback_data=f"edit_field:{subscription_id}:price",
    )

    builder.button(
        text="Дата платежа",
        callback_data=f"edit_field:{subscription_id}:next_payment_date",
    )

    builder.button(
        text="Категория",
        callback_data=f"edit_field:{subscription_id}:category",
    )

    builder.button(
        text="⬅️ Назад к карточке",
        callback_data=f"subscription:{subscription_id}",
    )

    builder.adjust(1)

    return builder.as_markup()

def get_settings_keyboard():
    builder = InlineKeyboardBuilder()

    builder.button(
        text="🔕 Отключить все напоминания",
        callback_data="disable_all_reminders",
    )

    builder.button(
        text="🔔 Включить все напоминания",
        callback_data="enable_all_reminders",
    )

    builder.adjust(1)

    return builder.as_markup()

def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [
            KeyboardButton(text="❌ Отмена"),
        ],
    ]

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
    )