import os


BOT_TOKEN = os.getenv("BOT_TOKEN", "8790909241:AAGWbTj-RdUsQu2JpkXtof56dlCtXUApgYg")

# Telegram Stars: provider_token всегда пустая строка, валюта XTR.
STARS_PROVIDER_TOKEN = ""

# Наборы кристаллов: ключ пакета -> кристаллы и цена в Stars (amount в LabeledPrice).
STAR_PACKAGES: dict[str, dict[str, int]] = {
    "20": {"crystals": 20, "stars": 90},
    "40": {"crystals": 40, "stars": 180},
    "80": {"crystals": 80, "stars": 360},
    "200": {"crystals": 200, "stars": 900},
    "500": {"crystals": 500, "stars": 2250},
    "1000": {"crystals": 1000, "stars": 4500},
}


def resolve_star_package(callback_data: str) -> tuple[str, dict[str, int]] | None:
    """
    Разбор callback_data кнопки покупки.
    Поддерживает buy:20 и старый формат buy:20:90.
    """
    if not callback_data.startswith("buy:"):
        return None
    parts = callback_data.split(":")
    if len(parts) < 2:
        return None

    package_key = parts[1]
    pack = STAR_PACKAGES.get(package_key)
    if pack:
        return package_key, pack

    # Старые кнопки: buy:20:90 — берём только количество кристаллов.
    crystals_raw = parts[1]
    for key, item in STAR_PACKAGES.items():
        if key == crystals_raw or str(item["crystals"]) == crystals_raw:
            return key, item
    return None

ADMIN_IDS = {
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}

ADMIN_USERNAMES = {
    x.strip().lstrip("@").lower()
    for x in os.getenv("ADMIN_USERNAMES", "guqca").split(",")
    if x.strip()
}

OPENAI_API_KEY = os.getenv(
    "OPENAI_API_KEY",
    "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",
)
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
WB_API_TOKEN = os.getenv("WB_API_TOKEN", "")

DB_PATH = os.getenv("DB_PATH", "wb_bot.sqlite3")
PRICE_PER_GENERATION = int(os.getenv("PRICE_PER_GENERATION", "10"))
MAX_GENERATIONS_PER_DAY = int(os.getenv("MAX_GENERATIONS_PER_DAY", "20"))
STARS_RATE = float(os.getenv("STARS_RATE", "4.5"))
SUPPORT_LINK = os.getenv("SUPPORT_LINK", "https://t.me/wb_card_support")
