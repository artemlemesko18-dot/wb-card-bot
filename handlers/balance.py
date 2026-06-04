from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, LabeledPrice, Message

import logging

from config import STAR_PACKAGES, STARS_PROVIDER_TOKEN, resolve_star_package

logger = logging.getLogger(__name__)
from keyboards.inline import crystal_packages_keyboard
from services import db

router = Router()


def build_crystal_packages() -> list[dict]:
    """Список пакетов для меню и инлайн-кнопок (из STAR_PACKAGES в config)."""
    return [
        {
            "key": key,
            "crystals": pack["crystals"],
            "stars": pack["stars"],
        }
        for key, pack in sorted(STAR_PACKAGES.items(), key=lambda item: int(item[0]))
    ]


def format_packages_menu_text() -> str:
    lines = ["✨ <b>Наборы кристаллов</b> ✨\n", "─────────────────────"]
    for pack in build_crystal_packages():
        lines.append(f"🌟 {pack['crystals']} кристаллов — {pack['stars']} ⭐")
    lines.extend(["─────────────────────\n", "Нажмите на нужный набор ниже 👇"])
    return "\n".join(lines)


@router.message(lambda m: m.text == "⭐ Баланс")
async def show_balance(message: Message) -> None:
    user = message.from_user
    if not user:
        return
    row = db.get_user(user.id)
    if row and row["is_blocked"]:
        await message.answer("🚫 Ваш аккаунт заблокирован. Обратитесь в поддержку.")
        return
    balance = db.get_balance(user.id)
    await message.answer(f"⭐ Ваш баланс: <b>{balance}</b> кристаллов", parse_mode="HTML")


@router.message(lambda m: m.text == "💰 Купить кристаллы")
async def buy_crystals_menu(message: Message) -> None:
    user = message.from_user
    if user:
        row = db.get_user(user.id)
        if row and row["is_blocked"]:
            await message.answer("🚫 Ваш аккаунт заблокирован. Обратитесь в поддержку.")
            return
    packages = build_crystal_packages()
    await message.answer(
        format_packages_menu_text(),
        parse_mode="HTML",
        reply_markup=crystal_packages_keyboard(packages),
    )


@router.callback_query(F.data.startswith("buy:"))
async def buy_package(callback: CallbackQuery) -> None:
    """Отправка инвойса Telegram Stars (XTR, пустой provider_token)."""
    if not callback.from_user or not callback.message:
        return

    row = db.get_user(callback.from_user.id)
    if row and row["is_blocked"]:
        await callback.message.answer("🚫 Ваш аккаунт заблокирован. Обратитесь в поддержку.")
        await callback.answer()
        return

    resolved = resolve_star_package(callback.data)
    if not resolved:
        await callback.message.answer(
            "⚠️ Устаревшее меню. Нажмите «💰 Купить кристаллы» ещё раз и выберите пакет.",
        )
        await callback.answer("Обновите меню покупки", show_alert=True)
        return
    package_key, pack = resolved

    crystals = pack["crystals"]
    stars_amount = pack["stars"]
    payload = f"crystals_{package_key}"

    try:
        await callback.message.answer_invoice(
            title=f"{crystals} кристаллов",
            description=f"Пакет на {crystals} кристаллов для генерации карточек WB",
            payload=payload,
            provider_token=STARS_PROVIDER_TOKEN,
            currency="XTR",
            prices=[LabeledPrice(label=f"{crystals} кристаллов", amount=stars_amount)],
        )
    except TelegramBadRequest as exc:
        logger.warning("Invoice error for package %s: %s", package_key, exc)
        await callback.message.answer("Оплата не выполнена. Попробуйте другой пакет или позже.")
    except Exception as exc:
        logger.exception("Invoice error for package %s: %s", package_key, exc)
        await callback.message.answer("Оплата не выполнена. Попробуйте позже.")

    await callback.answer()
