from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from config import ADMIN_IDS, ADMIN_USERNAMES


def _is_admin(user_id: int, username: str | None) -> bool:
    return user_id in ADMIN_IDS or ((username or "").lower() in ADMIN_USERNAMES)


def main_menu_keyboard(user_id: int, username: str | None = None) -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="✨ Создать карточку WB")],
        [KeyboardButton(text="⭐ Баланс"), KeyboardButton(text="💰 Купить кристаллы")],
        [KeyboardButton(text="🆘 Помощь")],
    ]
    if _is_admin(user_id, username):
        buttons.append([KeyboardButton(text="🛠 Админ-панель")])

    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
