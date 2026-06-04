from aiogram import Router
from aiogram.filters import Command
from aiogram.filters import CommandStart
from aiogram.types import Message

from config import SUPPORT_LINK
from keyboards.reply import main_menu_keyboard
from services import db

router = Router()


def _is_blocked(user_id: int) -> bool:
    row = db.get_user(user_id)
    return bool(row and row["is_blocked"])


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    user = message.from_user
    if not user:
        return
    db.upsert_user(user.id, user.username, user.first_name)
    if _is_blocked(user.id):
        await message.answer("🚫 Ваш аккаунт заблокирован. Обратитесь в поддержку.")
        return
    price = int(db.get_setting("price_per_generation", "10"))

    await message.answer(
        (
            "👋 <b>Добро пожаловать в WB Card Bot</b>\n\n"
            "Создавайте карточки товаров для Wildberries за кристаллы.\n"
            f"1 генерация = {price} кристаллов."
        ),
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(user.id, user.username),
    )


@router.message(Command("myid"))
async def my_id(message: Message) -> None:
    if not message.from_user:
        return
    await message.answer(
        f"Ваш Telegram ID: <code>{message.from_user.id}</code>\n"
        f"Username: @{message.from_user.username or '-'}",
        parse_mode="HTML",
    )


@router.message(lambda m: m.text == "🆘 Помощь")
async def help_message(message: Message) -> None:
    if not message.from_user:
        return
    if _is_blocked(message.from_user.id):
        await message.answer("🚫 Ваш аккаунт заблокирован. Обратитесь в поддержку.")
        return
    price = int(db.get_setting("price_per_generation", "10"))
    await message.answer(
        (
            "🆘 <b>Как пользоваться ботом</b>\n\n"
            "1) Нажмите <b>💰 Купить кристаллы</b>\n"
            "2) Пополните баланс через Telegram Stars\n"
            "3) Нажмите <b>✨ Создать карточку WB</b>\n"
            "4) Пройдите шаги мастера и подтвердите генерацию\n\n"
            f"💎 Стоимость генерации: <b>{price} кристаллов</b>\n"
            f"📞 Поддержка: <a href='{SUPPORT_LINK}'>связаться</a>"
        ),
        parse_mode="HTML",
    )
