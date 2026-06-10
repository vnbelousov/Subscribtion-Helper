from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from data_access_module.database import async_session
from command_module.keyboards import (
    get_billing_period_keyboard,
    get_cancel_keyboard,
    get_categories_keyboard,
    get_edit_subscription_keyboard,
    get_main_menu,
    get_settings_keyboard,
    get_subscription_actions_keyboard,
    get_subscriptions_keyboard,
)
from subscription_module.category_service import get_all_categories, get_category_by_id
from subscription_module.subscription_service import (
    archive_subscription,
    create_subscription,
    get_active_subscriptions_by_user,
    get_subscription_by_id,
    toggle_subscription_reminders,
    update_subscription_category,
    update_subscription_next_payment_date,
    update_subscription_price,
    update_subscription_service_name,
    disable_all_reminders_by_user,
    enable_all_reminders_by_user,
)
from subscription_module.user_service import get_or_create_user
from utils.date_utils import parse_date
from statistics_module.statistics_service import build_statistics_report


router = Router()

@router.message(F.text == "❌ Отмена")
async def cancel_action(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()

    if current_state is None:
        await message.answer(
            "Сейчас нет активного действия для отмены.",
            reply_markup=get_main_menu(),
        )
        return

    await state.clear()

    await message.answer(
        "Действие отменено.",
        reply_markup=get_main_menu(),
    )


class AddSubscriptionStates(StatesGroup):
    waiting_for_service_name = State()
    waiting_for_price = State()
    waiting_for_billing_period = State()
    waiting_for_next_payment_date = State()
    waiting_for_category = State()

class EditSubscriptionStates(StatesGroup):
    waiting_for_new_service_name = State()
    waiting_for_new_price = State()
    waiting_for_new_next_payment_date = State()
    waiting_for_new_category = State()


@router.message(F.text == "➕ Добавить подписку")
async def add_subscription_start(
    message: Message,
    state: FSMContext,
) -> None:
    await state.clear()

    await message.answer(
        "Введите название сервиса.\n\n"
        "Например: Яндекс Плюс",
        reply_markup=get_cancel_keyboard(),
    )

    await state.set_state(AddSubscriptionStates.waiting_for_service_name)


@router.message(AddSubscriptionStates.waiting_for_service_name)
async def process_service_name(
    message: Message,
    state: FSMContext,
) -> None:
    service_name = message.text.strip()

    if len(service_name) < 2:
        await message.answer(
            "Название слишком короткое. Введите название сервиса ещё раз."
        )
        return

    await state.update_data(service_name=service_name)

    await message.answer(
        "Введите стоимость подписки в рублях.\n\n"
        "Например: 399",
        reply_markup=get_cancel_keyboard(),
    )

    await state.set_state(AddSubscriptionStates.waiting_for_price)


@router.message(AddSubscriptionStates.waiting_for_price)
async def process_price(
    message: Message,
    state: FSMContext,
) -> None:
    raw_price = message.text.strip().replace(",", ".")

    try:
        price = Decimal(raw_price)
    except InvalidOperation:
        await message.answer(
            "Стоимость должна быть числом.\n\n"
            "Например: 399 или 399.99"
        )
        return

    if price <= 0:
        await message.answer(
            "Стоимость должна быть больше нуля. Введите стоимость ещё раз."
        )
        return

    await state.update_data(price=str(price))

    await message.answer(
        "Выберите периодичность списания:",
        reply_markup=get_billing_period_keyboard(),
    )

    await state.set_state(AddSubscriptionStates.waiting_for_billing_period)


@router.callback_query(
    AddSubscriptionStates.waiting_for_billing_period,
    F.data.startswith("period:"),
)
async def process_billing_period(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    billing_period = callback.data.split(":")[1]

    await state.update_data(billing_period=billing_period)

    await callback.message.answer(
        "Введите дату следующего платежа в формате ДД.ММ.ГГГГ.\n\n"
        "Например: 15.06.2026",
        reply_markup=get_cancel_keyboard(),
    )

    await state.set_state(AddSubscriptionStates.waiting_for_next_payment_date)

    await callback.answer()


@router.message(AddSubscriptionStates.waiting_for_next_payment_date)
async def process_next_payment_date(
    message: Message,
    state: FSMContext,
) -> None:
    next_payment_date = parse_date(message.text.strip())

    if next_payment_date is None:
        await message.answer(
            "Дата введена неверно. Используйте формат ДД.ММ.ГГГГ.\n\n"
            "Например: 15.06.2026"
        )
        return

    await state.update_data(next_payment_date=next_payment_date.isoformat())

    async with async_session() as session:
        categories = await get_all_categories(session)

    await message.answer(
        "Выберите категорию подписки:",
        reply_markup=get_categories_keyboard(categories),
    )

    await state.set_state(AddSubscriptionStates.waiting_for_category)


@router.callback_query(
    AddSubscriptionStates.waiting_for_category,
    F.data.startswith("category:"),
)
async def process_category(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    category_id = int(callback.data.split(":")[1])

    data = await state.get_data()

    async with async_session() as session:
        user = await get_or_create_user(session, callback.from_user)
        category = await get_category_by_id(session, category_id)

        if category is None:
            await callback.message.answer(
                "Категория не найдена. Попробуйте добавить подписку заново."
            )
            await state.clear()
            await callback.answer()
            return

        subscription = await create_subscription(
            session=session,
            user=user,
            category_id=category.id,
            service_name=data["service_name"],
            price=Decimal(data["price"]),
            billing_period=data["billing_period"],
            next_payment_date=parse_date_from_iso(data["next_payment_date"]),
        )

    period_text = get_period_text(subscription.billing_period)

    await callback.message.answer(
        "Подписка успешно добавлена.\n\n"
        f"Сервис: {subscription.service_name}\n"
        f"Стоимость: {subscription.price} {subscription.currency}\n"
        f"Периодичность: {period_text}\n"
        f"Дата следующего платежа: "
        f"{subscription.next_payment_date.strftime('%d.%m.%Y')}\n"
        f"Категория: {category.icon} {category.name}",
        reply_markup=get_main_menu(),
    )

    await state.clear()
    await callback.answer()


def parse_date_from_iso(value: str):
    from datetime import date

    return date.fromisoformat(value)


def get_period_text(period: str) -> str:
    periods = {
        "monthly": "ежемесячно",
        "quarterly": "ежеквартально",
        "yearly": "ежегодно",
    }

    return periods.get(period, period)

@router.message(F.text == "📋 Мои подписки")
async def show_subscriptions(message: Message) -> None:
    async with async_session() as session:
        user = await get_or_create_user(session, message.from_user)
        subscriptions = await get_active_subscriptions_by_user(session, user)

    if not subscriptions:
        await message.answer(
            "У вас пока нет активных подписок.\n\n"
            "Нажмите «➕ Добавить подписку», чтобы добавить первую."
        )
        return

    text = "Ваши активные подписки:\n\n"

    for index, subscription in enumerate(subscriptions, start=1):
        next_payment_date = subscription.next_payment_date.strftime("%d.%m.%Y")

        text += (
            f"{index}. {subscription.service_name} — "
            f"{subscription.price} {subscription.currency}, "
            f"следующий платёж {next_payment_date}\n"
        )

    text += "\nВыберите подписку, чтобы посмотреть подробности."

    await message.answer(
        text,
        reply_markup=get_subscriptions_keyboard(subscriptions),
    )


@router.callback_query(F.data.startswith("subscription:"))
async def show_subscription_card(callback: CallbackQuery) -> None:
    subscription_id = int(callback.data.split(":")[1])

    async with async_session() as session:
        user = await get_or_create_user(session, callback.from_user)
        subscription = await get_subscription_by_id(
            session=session,
            subscription_id=subscription_id,
            user=user,
        )

    if subscription is None:
        await callback.message.answer(
            "Подписка не найдена или уже недоступна."
        )
        await callback.answer()
        return

    period_text = get_period_text(subscription.billing_period)
    next_payment_date = subscription.next_payment_date.strftime("%d.%m.%Y")

    reminders_text = (
        f"включены, за {subscription.reminder_days_before} дн."
        if subscription.reminders_enabled
        else "отключены"
    )

    management_url_text = (
        subscription.management_url
        if subscription.management_url
        else "не указана"
    )

    text = (
        f"Карточка подписки\n\n"
        f"Сервис: {subscription.service_name}\n"
        f"Стоимость: {subscription.price} {subscription.currency}\n"
        f"Периодичность: {period_text}\n"
        f"Дата следующего платежа: {next_payment_date}\n"
        f"Категория: {subscription.category.icon} {subscription.category.name}\n"
        f"Напоминания: {reminders_text}\n"
        f"Ссылка управления: {management_url_text}"
    )

    await callback.message.answer(
        text,
        reply_markup=get_subscription_actions_keyboard(
            subscription.id,
            subscription.reminders_enabled,
        ),
    )

    await callback.answer()


@router.callback_query(F.data.startswith("archive_subscription:"))
async def archive_subscription_callback(callback: CallbackQuery) -> None:
    subscription_id = int(callback.data.split(":")[1])

    async with async_session() as session:
        user = await get_or_create_user(session, callback.from_user)
        subscription = await get_subscription_by_id(
            session=session,
            subscription_id=subscription_id,
            user=user,
        )

        if subscription is None:
            await callback.message.answer(
                "Подписка не найдена или уже была архивирована."
            )
            await callback.answer()
            return

        await archive_subscription(session, subscription)

    await callback.message.answer(
        "Подписка перенесена в архив.\n\n"
        "Она больше не будет отображаться в активных подписках "
        "и не будет учитываться в напоминаниях."
    )

    await callback.answer()


@router.callback_query(F.data == "back_to_subscriptions")
async def back_to_subscriptions(callback: CallbackQuery) -> None:
    async with async_session() as session:
        user = await get_or_create_user(session, callback.from_user)
        subscriptions = await get_active_subscriptions_by_user(session, user)

    if not subscriptions:
        await callback.message.answer(
            "У вас пока нет активных подписок."
        )
        await callback.answer()
        return

    text = "Ваши активные подписки:\n\n"

    for index, subscription in enumerate(subscriptions, start=1):
        next_payment_date = subscription.next_payment_date.strftime("%d.%m.%Y")

        text += (
            f"{index}. {subscription.service_name} — "
            f"{subscription.price} {subscription.currency}, "
            f"следующий платёж {next_payment_date}\n"
        )

    text += "\nВыберите подписку, чтобы посмотреть подробности."

    await callback.message.answer(
        text,
        reply_markup=get_subscriptions_keyboard(subscriptions),
    )

    await callback.answer()

@router.callback_query(F.data.startswith("toggle_reminders:"))
async def toggle_reminders_callback(callback: CallbackQuery) -> None:
    subscription_id = int(callback.data.split(":")[1])

    async with async_session() as session:
        user = await get_or_create_user(session, callback.from_user)
        subscription = await get_subscription_by_id(
            session=session,
            subscription_id=subscription_id,
            user=user,
        )

        if subscription is None:
            await callback.message.answer(
                "Подписка не найдена или уже недоступна."
            )
            await callback.answer()
            return

        subscription = await toggle_subscription_reminders(session, subscription)

    if subscription.reminders_enabled:
        result_text = "Напоминания по подписке включены."
    else:
        result_text = "Напоминания по подписке отключены."

    await callback.message.answer(result_text)

    await callback.answer()

@router.message(F.text == "📊 Статистика")
async def show_statistics(message: Message) -> None:
    async with async_session() as session:
        user = await get_or_create_user(session, message.from_user)
        subscriptions = await get_active_subscriptions_by_user(session, user)

    report = build_statistics_report(subscriptions)

    await message.answer(report)

@router.callback_query(F.data.startswith("edit_subscription:"))
async def edit_subscription_menu(callback: CallbackQuery) -> None:
    subscription_id = int(callback.data.split(":")[1])

    async with async_session() as session:
        user = await get_or_create_user(session, callback.from_user)
        subscription = await get_subscription_by_id(
            session=session,
            subscription_id=subscription_id,
            user=user,
        )

    if subscription is None:
        await callback.message.answer(
            "Подписка не найдена или уже недоступна."
        )
        await callback.answer()
        return

    await callback.message.answer(
        "Выберите, что нужно изменить:",
        reply_markup=get_edit_subscription_keyboard(subscription.id),
    )

    await callback.answer()

@router.callback_query(F.data.startswith("edit_field:"))
async def edit_subscription_field(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split(":")
    subscription_id = int(parts[1])
    field_name = parts[2]

    await state.update_data(subscription_id=subscription_id)

    if field_name == "service_name":
        await callback.message.answer(
            "Введите новое название сервиса.\n\n"
            "Например: Кинопоиск",
            reply_markup=get_cancel_keyboard(),
        )
        await state.set_state(EditSubscriptionStates.waiting_for_new_service_name)

    elif field_name == "price":
        await callback.message.answer(
            "Введите новую стоимость подписки.\n\n"
            "Например: 399",
            reply_markup=get_cancel_keyboard(),
        )
        await state.set_state(EditSubscriptionStates.waiting_for_new_price)

    elif field_name == "next_payment_date":
        await callback.message.answer(
            "Введите новую дату следующего платежа в формате ДД.ММ.ГГГГ.\n\n"
            "Например: 15.06.2026",
            reply_markup = get_cancel_keyboard(),
        )
        await state.set_state(EditSubscriptionStates.waiting_for_new_next_payment_date)

    elif field_name == "category":
        async with async_session() as session:
            categories = await get_all_categories(session)

        await callback.message.answer(
            "Выберите новую категорию:",
            reply_markup=get_categories_keyboard(categories),
        )
        await state.set_state(EditSubscriptionStates.waiting_for_new_category)

    await callback.answer()

@router.message(EditSubscriptionStates.waiting_for_new_service_name)
async def process_new_service_name(message: Message, state: FSMContext) -> None:
    new_service_name = message.text.strip()

    if len(new_service_name) < 2:
        await message.answer(
            "Название слишком короткое. Введите название сервиса ещё раз."
        )
        return

    data = await state.get_data()
    subscription_id = data["subscription_id"]

    async with async_session() as session:
        user = await get_or_create_user(session, message.from_user)
        subscription = await get_subscription_by_id(
            session=session,
            subscription_id=subscription_id,
            user=user,
        )

        if subscription is None:
            await message.answer("Подписка не найдена.")
            await state.clear()
            return

        await update_subscription_service_name(
            session=session,
            subscription=subscription,
            service_name=new_service_name,
        )

    await state.clear()

    await message.answer(
        "Название подписки обновлено.",
        reply_markup=get_main_menu(),
    )

@router.message(EditSubscriptionStates.waiting_for_new_price)
async def process_new_price(message: Message, state: FSMContext) -> None:
    raw_price = message.text.strip().replace(",", ".")

    try:
        price = Decimal(raw_price)
    except InvalidOperation:
        await message.answer(
            "Стоимость должна быть числом.\n\n"
            "Например: 399 или 399.99"
        )
        return

    if price <= 0:
        await message.answer(
            "Стоимость должна быть больше нуля. Введите стоимость ещё раз."
        )
        return

    data = await state.get_data()
    subscription_id = data["subscription_id"]

    async with async_session() as session:
        user = await get_or_create_user(session, message.from_user)
        subscription = await get_subscription_by_id(
            session=session,
            subscription_id=subscription_id,
            user=user,
        )

        if subscription is None:
            await message.answer("Подписка не найдена.")
            await state.clear()
            return

        await update_subscription_price(
            session=session,
            subscription=subscription,
            price=price,
        )

    await state.clear()

    await message.answer(
        "Стоимость подписки обновлена.",
        reply_markup=get_main_menu(),
    )

@router.message(EditSubscriptionStates.waiting_for_new_next_payment_date)
async def process_new_next_payment_date(message: Message, state: FSMContext) -> None:
    next_payment_date = parse_date(message.text.strip())

    if next_payment_date is None:
        await message.answer(
            "Дата введена неверно. Используйте формат ДД.ММ.ГГГГ.\n\n"
            "Например: 15.06.2026"
        )
        return

    data = await state.get_data()
    subscription_id = data["subscription_id"]

    async with async_session() as session:
        user = await get_or_create_user(session, message.from_user)
        subscription = await get_subscription_by_id(
            session=session,
            subscription_id=subscription_id,
            user=user,
        )

        if subscription is None:
            await message.answer("Подписка не найдена.")
            await state.clear()
            return

        await update_subscription_next_payment_date(
            session=session,
            subscription=subscription,
            next_payment_date=next_payment_date,
        )

    await state.clear()

    await message.answer(
        "Дата следующего платежа обновлена.",
        reply_markup=get_main_menu(),
    )

@router.callback_query(
    EditSubscriptionStates.waiting_for_new_category,
    F.data.startswith("category:"),
)
async def process_new_category(callback: CallbackQuery, state: FSMContext) -> None:
    category_id = int(callback.data.split(":")[1])

    data = await state.get_data()
    subscription_id = data["subscription_id"]

    async with async_session() as session:
        user = await get_or_create_user(session, callback.from_user)
        subscription = await get_subscription_by_id(
            session=session,
            subscription_id=subscription_id,
            user=user,
        )

        category = await get_category_by_id(session, category_id)

        if subscription is None:
            await callback.message.answer("Подписка не найдена.")
            await state.clear()
            await callback.answer()
            return

        if category is None:
            await callback.message.answer("Категория не найдена.")
            await state.clear()
            await callback.answer()
            return

        await update_subscription_category(
            session=session,
            subscription=subscription,
            category_id=category.id,
        )

    await state.clear()

    await callback.message.answer(
        "Категория подписки обновлена.",
        reply_markup=get_main_menu(),
    )

    await callback.answer()

@router.message(F.text == "⚙️ Настройки")
async def show_settings(message: Message) -> None:
    await message.answer(
        "Настройки напоминаний.\n\n"
        "Здесь можно включить или отключить напоминания сразу для всех активных подписок.",
        reply_markup=get_settings_keyboard(),
    )

@router.callback_query(F.data == "disable_all_reminders")
async def disable_all_reminders_callback(callback: CallbackQuery) -> None:
    async with async_session() as session:
        user = await get_or_create_user(session, callback.from_user)
        changed_count = await disable_all_reminders_by_user(session, user)

    if changed_count == 0:
        await callback.message.answer(
            "Активных подписок с включёнными напоминаниями не найдено."
        )
    else:
        await callback.message.answer(
            f"Напоминания отключены для активных подписок: {changed_count}."
        )

    await callback.answer()

@router.callback_query(F.data == "enable_all_reminders")
async def enable_all_reminders_callback(callback: CallbackQuery) -> None:
    async with async_session() as session:
        user = await get_or_create_user(session, callback.from_user)
        changed_count = await enable_all_reminders_by_user(session, user)

    if changed_count == 0:
        await callback.message.answer(
            "Активных подписок с отключёнными напоминаниями не найдено."
        )
    else:
        await callback.message.answer(
            f"Напоминания включены для активных подписок: {changed_count}."
        )

    await callback.answer()