import json

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import ADMIN_IDS, ADMIN_USERNAMES
from keyboards.inline import admin_menu_keyboard, users_manage_keyboard
from services import db, refresh_wb_categories_cache
from states import FSMAdmin

router = Router()


def is_admin(user_id: int, username: str | None = None) -> bool:
    return user_id in ADMIN_IDS or ((username or "").lower() in ADMIN_USERNAMES)


@router.message(lambda m: m.text == "🛠 Админ-панель")
async def admin_panel(message: Message) -> None:
    if not message.from_user or not is_admin(message.from_user.id, message.from_user.username):
        return
    await message.answer("🛠 <b>Админ-панель</b>", parse_mode="HTML", reply_markup=admin_menu_keyboard())


@router.callback_query(F.data == "admin:users")
async def admin_users(callback: CallbackQuery) -> None:
    if not callback.from_user or not is_admin(callback.from_user.id, callback.from_user.username):
        return
    users = db.list_users(limit=10)
    if not users:
        await callback.message.answer("Пользователи не найдены.")
        await callback.answer()
        return
    for row in users:
        text = (
            f"ID: <code>{row['user_id']}</code>\n"
            f"Username: @{row['username'] or '-'}\n"
            f"Баланс: {row['balance']} кристаллов\n"
            f"Заблокирован: {'Да' if row['is_blocked'] else 'Нет'}\n"
            f"Дата: {row['registered_at']}"
        )
        await callback.message.answer(text, parse_mode="HTML", reply_markup=users_manage_keyboard(int(row["user_id"])))
    await callback.answer()


@router.callback_query(F.data.startswith("admin:add:") | F.data.startswith("admin:sub:"))
async def admin_balance_op(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.from_user or not is_admin(callback.from_user.id, callback.from_user.username):
        return
    action, user_id = callback.data.split(":")[1], int(callback.data.split(":")[2])
    await state.set_state(FSMAdmin.waiting_for_crystals_amount)
    await state.update_data(target_user_id=user_id, action=action)
    await callback.message.answer(
        f"Введите количество кристаллов для {'начисления' if action == 'add' else 'списания'} пользователю {user_id}:"
    )
    await callback.answer()


@router.message(FSMAdmin.waiting_for_crystals_amount)
async def admin_balance_amount(message: Message, state: FSMContext) -> None:
    if not message.from_user or not is_admin(message.from_user.id, message.from_user.username):
        await state.clear()
        return
    if not message.text or not message.text.isdigit():
        await message.answer("Введите положительное число.")
        return
    amount = int(message.text)
    data = await state.get_data()
    target_user_id = int(data["target_user_id"])
    action = data["action"]
    signed_amount = amount if action == "add" else -amount
    ok = db.change_balance(target_user_id, signed_amount, "admin_adjust", stars_amount=0)
    if ok:
        await message.answer("✅ Баланс обновлен.")
    else:
        await message.answer("❌ Не удалось изменить баланс.")
    await state.clear()


@router.callback_query(F.data.startswith("admin:block:") | F.data.startswith("admin:unblock:"))
async def admin_block_toggle(callback: CallbackQuery) -> None:
    if not callback.from_user or not is_admin(callback.from_user.id, callback.from_user.username):
        return
    parts = callback.data.split(":")
    mode = parts[1]
    user_id = int(parts[2])
    db.set_user_blocked(user_id, mode == "block")
    await callback.message.answer("✅ Статус пользователя обновлен.")
    await callback.answer()


@router.callback_query(F.data == "admin:generations")
async def admin_generations(callback: CallbackQuery) -> None:
    if not callback.from_user or not is_admin(callback.from_user.id, callback.from_user.username):
        return
    items = db.list_generations(limit=10)
    if not items:
        await callback.message.answer("Генераций пока нет.")
        await callback.answer()
        return
    for row in items:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔁 Отправить результат пользователю",
                        callback_data=f"admin:resend:{int(row['id'])}",
                    )
                ]
            ]
        )
        await callback.message.answer(
            f"ID: <code>{row['id']}</code> | User: <code>{row['user_id']}</code>\n"
            f"{row['product_name']} | status={row['status']}",
            parse_mode="HTML",
            reply_markup=kb,
        )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:resend:"))
async def admin_resend_generation(callback: CallbackQuery) -> None:
    if not callback.from_user or not is_admin(callback.from_user.id, callback.from_user.username):
        return
    if not callback.message:
        return
    generation_id = int(callback.data.split(":")[2])
    row = db.get_generation(generation_id)
    if not row:
        await callback.message.answer("❌ Генерация не найдена.")
        await callback.answer()
        return
    result = json.loads(row["result_json"] or "{}")
    text = (
        "🔁 <b>Повтор результата генерации</b>\n\n"
        f"<b>Название:</b> {result.get('title', row['product_name'])}\n"
        f"<b>Описание:</b> {result.get('description', row['description'] or '-')}\n"
        f"<b>Характеристики:</b> {result.get('characteristics', {})}\n"
        f"<b>Изображение:</b> {result.get('image_link', '-')}\n\n"
        f"ID генерации: <code>{row['id']}</code>"
    )
    try:
        await callback.bot.send_message(int(row["user_id"]), text, parse_mode="HTML")
        await callback.message.answer("✅ Результат повторно отправлен пользователю.")
    except Exception as exc:
        await callback.message.answer(f"❌ Не удалось отправить пользователю: {exc}")
    await callback.answer()


@router.callback_query(F.data == "admin:stats")
async def admin_stats(callback: CallbackQuery) -> None:
    if not callback.from_user or not is_admin(callback.from_user.id, callback.from_user.username):
        return
    stats = db.get_stats()
    await callback.message.answer(
        (
            "📊 <b>Статистика</b>\n\n"
            f"Пользователи: <b>{stats['users']}</b>\n"
            f"Генерации: <b>{stats['generations']}</b>\n"
            f"Продано кристаллов: <b>{stats['sold_crystals']}</b>\n"
            f"Выручка (Stars): <b>{stats['revenue_stars']}</b>"
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "admin:settings")
async def admin_settings(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.from_user or not is_admin(callback.from_user.id, callback.from_user.username):
        return
    await state.set_state(FSMAdmin.waiting_for_setting_value)
    await callback.message.answer(
        "Отправьте настройку в формате:\n"
        "<code>price_per_generation=10</code>\n"
        "<code>stars_rate=4.5</code>\n"
        "<code>max_generations_per_day=20</code>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(FSMAdmin.waiting_for_setting_value)
async def admin_setting_value(message: Message, state: FSMContext) -> None:
    if not message.from_user or not is_admin(message.from_user.id, message.from_user.username):
        await state.clear()
        return
    if not message.text or "=" not in message.text:
        await message.answer("Неверный формат.")
        return
    key, value = [x.strip() for x in message.text.split("=", 1)]
    if key not in {"price_per_generation", "stars_rate", "max_generations_per_day"}:
        await message.answer("Недопустимый ключ.")
        return
    db.set_setting(key, value)
    await message.answer("✅ Настройка сохранена.")
    await state.clear()


@router.callback_query(F.data == "admin:broadcast")
async def admin_broadcast_request(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.from_user or not is_admin(callback.from_user.id, callback.from_user.username):
        return
    await state.set_state(FSMAdmin.waiting_for_broadcast_text)
    await callback.message.answer("Введите текст рассылки:")
    await callback.answer()


@router.callback_query(F.data == "admin:refresh_wb_categories")
async def admin_refresh_wb_categories(callback: CallbackQuery) -> None:
    if not callback.from_user or not is_admin(callback.from_user.id, callback.from_user.username):
        return
    if not callback.message:
        return
    wait = await callback.message.answer("🔄 Обновляю категории WB...")
    try:
        count = await refresh_wb_categories_cache()
        await wait.edit_text(f"✅ Категории WB обновлены: {count}")
    except Exception as exc:
        await wait.edit_text(f"❌ Не удалось обновить категории WB: {exc}")
    await callback.answer()


@router.message(FSMAdmin.waiting_for_broadcast_text)
async def admin_broadcast_send(message: Message, state: FSMContext) -> None:
    if not message.from_user or not is_admin(message.from_user.id, message.from_user.username):
        await state.clear()
        return
    users = db.list_users(limit=100000)
    sent = 0
    for user in users:
        try:
            await message.bot.send_message(int(user["user_id"]), message.text or "")
            sent += 1
        except Exception:
            continue
    await message.answer(f"📢 Рассылка завершена. Отправлено: {sent}")
    await state.clear()
