from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def categories_keyboard(categories: list[dict], include_show_all: bool = False) -> InlineKeyboardMarkup:
    rows = []
    for cat in categories[:20]:
        rows.append(
            [
                InlineKeyboardButton(
                    text=cat.get("name", f"Категория {cat.get('id', '')}"),
                    callback_data=f"cat:{cat.get('id')}",
                )
            ]
        )
    if include_show_all:
        rows.append([InlineKeyboardButton(text="📚 Показать все категории", callback_data="cat:all")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def suggested_categories_keyboard(categories: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for cat in categories[:5]:
        label = cat.get("name", f"Категория {cat.get('id', '')}")
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"🤖 {label}",
                    callback_data=f"cat:{cat.get('id')}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="🔎 Не нашёл, показать все", callback_data="cat:all")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def generation_confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data="gen:confirm"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="gen:cancel"),
            ]
        ]
    )


def crystal_packages_keyboard(packages: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for pack in packages:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{pack['crystals']} кристаллов — {pack['stars']}⭐",
                    callback_data=f"buy:{pack['key']}",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin:users")],
            [InlineKeyboardButton(text="🧾 Генерации", callback_data="admin:generations")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats")],
            [InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin:settings")],
            [InlineKeyboardButton(text="🔄 Обновить WB категории", callback_data="admin:refresh_wb_categories")],
            [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin:broadcast")],
        ]
    )


def users_manage_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Начислить", callback_data=f"admin:add:{user_id}"),
                InlineKeyboardButton(text="➖ Списать", callback_data=f"admin:sub:{user_id}"),
            ],
            [
                InlineKeyboardButton(text="🚫 Блок", callback_data=f"admin:block:{user_id}"),
                InlineKeyboardButton(text="✅ Разблок", callback_data=f"admin:unblock:{user_id}"),
            ],
        ]
    )
