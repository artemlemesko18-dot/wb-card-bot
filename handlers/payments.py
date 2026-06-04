from aiogram import F, Router
from aiogram.types import Message, PreCheckoutQuery

from config import STAR_PACKAGES
from services import db

router = Router()


def parse_crystal_payload(payload: str) -> tuple[str, int, int] | None:
    """
    Разбор invoice_payload вида crystals_20 -> (package_key, crystals, stars).
    Возвращает None, если payload не относится к покупке кристаллов.
    """
    if not payload.startswith("crystals_"):
        return None
    package_key = payload.removeprefix("crystals_")
    pack = STAR_PACKAGES.get(package_key)
    if not pack:
        return None
    return package_key, pack["crystals"], pack["stars"]


@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery) -> None:
    """
    Обязательная предварительная проверка перед списанием Stars.
    Подтверждаем только валидные payload из STAR_PACKAGES.
    """
    parsed = parse_crystal_payload(pre_checkout_query.invoice_payload)
    if not parsed:
        await pre_checkout_query.answer(ok=False, error_message="Оплата не выполнена")
        return

    # Подтверждаем оплату; сумму для транзакции берём из фактического инвойса.
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def process_successful_payment(message: Message) -> None:
    """Начисление кристаллов после успешной оплаты Telegram Stars."""
    user = message.from_user
    if not user or not message.successful_payment:
        return

    payment = message.successful_payment
    parsed = parse_crystal_payload(payment.invoice_payload)
    if not parsed:
        await message.answer("Оплата не выполнена")
        return

    _package_key, crystals, _stars = parsed
    paid_stars = payment.total_amount

    db.upsert_user(user.id, user.username, user.first_name)
    credited = db.change_balance(user.id, crystals, "purchase", stars_amount=paid_stars)
    if not credited:
        await message.answer("Оплата не выполнена")
        return

    await message.answer(
        f"✅ Оплата прошла успешно! Вам начислено <b>{crystals}</b> кристаллов.",
        parse_mode="HTML",
    )
