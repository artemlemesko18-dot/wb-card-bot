import json

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from ai_categories import suggest_categories
from keyboards.inline import categories_keyboard, generation_confirmation_keyboard, suggested_categories_keyboard
from pollinations_api import generate_image_via_pollinations
from services import db
from states import FSMGeneration

router = Router()


async def _load_categories() -> list[dict]:
    # Expanded local categories (no WB token required).
    return [
        {"id": 1001, "name": "Женская одежда"},
        {"id": 1002, "name": "Мужская одежда"},
        {"id": 1003, "name": "Обувь"},
        {"id": 1004, "name": "Сумки и рюкзаки"},
        {"id": 1005, "name": "Украшения и аксессуары"},
        {"id": 1006, "name": "Косметика"},
        {"id": 1007, "name": "Парфюмерия"},
        {"id": 1008, "name": "Маникюр и ногти"},
        {"id": 1009, "name": "Техника и электроника"},
        {"id": 1010, "name": "Смартфоны и аксессуары"},
        {"id": 1011, "name": "Компьютеры и ноутбуки"},
        {"id": 1012, "name": "Бытовая техника"},
        {"id": 1013, "name": "Товары для дома"},
        {"id": 1014, "name": "Текстиль и постель"},
        {"id": 1015, "name": "Мебель"},
        {"id": 1016, "name": "Детские товары"},
        {"id": 1017, "name": "Игрушки"},
        {"id": 1018, "name": "Книги"},
        {"id": 1019, "name": "Канцелярия"},
        {"id": 1020, "name": "Спорт и отдых"},
        {"id": 1021, "name": "Туризм и кемпинг"},
        {"id": 1022, "name": "Автотовары"},
        {"id": 1023, "name": "Зоотовары"},
        {"id": 1024, "name": "Продукты питания"},
        {"id": 1025, "name": "Товары для здоровья"},
        {"id": 1026, "name": "Инструменты и ремонт"},
        {"id": 1027, "name": "Сад и дача"},
        {"id": 1028, "name": "Подарки и сувениры"},
        {"id": 1029, "name": "Нижнее белье"},
        {"id": 1030, "name": "Товары для животных"},
    ]


def _suggest_categories(product_name: str, categories: list[dict]) -> list[dict]:
    text = product_name.lower()
    keyword_to_category_ids = {
        "чехол": [1010, 1005],
        "телефон": [1010, 1009],
        "iphone": [1010],
        "samsung": [1010],
        "ноутбук": [1011, 1009],
        "клавиатур": [1011, 1009],
        "мыш": [1011, 1009],
        "крем": [1006, 1025],
        "сыворот": [1006],
        "помад": [1006],
        "духи": [1007],
        "маникюр": [1008, 1006],
        "лак": [1008],
        "плать": [1001],
        "юбк": [1001],
        "джинс": [1001, 1002],
        "футболк": [1001, 1002],
        "кроссов": [1003, 1020],
        "ботинк": [1003],
        "сумк": [1004],
        "рюкзак": [1004],
        "браслет": [1005],
        "кольц": [1005],
        "серьг": [1005],
        "подушка": [1014, 1013],
        "одеял": [1014],
        "стол": [1015],
        "стул": [1015],
        "детск": [1016, 1017],
        "игруш": [1017],
        "книга": [1018],
        "ежедневник": [1019],
        "ручк": [1019],
        "велосипед": [1020],
        "гантел": [1020],
        "палатк": [1021],
        "авто": [1022],
        "кошк": [1023, 1030],
        "собак": [1023, 1030],
        "витамин": [1025],
        "дрель": [1026],
        "шуруповерт": [1026],
        "семена": [1027],
        "подар": [1028],
        "белье": [1029],
    }
    category_map = {int(c["id"]): c for c in categories}
    matched_ids: list[int] = []
    for keyword, ids in keyword_to_category_ids.items():
        if keyword in text:
            for category_id in ids:
                if category_id not in matched_ids:
                    matched_ids.append(category_id)

    if matched_ids:
        suggested = [category_map[cid] for cid in matched_ids if cid in category_map]
        # Add popular fallback categories to ensure enough options.
        popular_ids = [1001, 1002, 1003, 1006, 1009, 1010, 1013, 1020]
        for cid in popular_ids:
            if cid in category_map and cid not in matched_ids:
                suggested.append(category_map[cid])
        return suggested[:12]

    popular_ids = [1001, 1002, 1003, 1006, 1009, 1010, 1013, 1016, 1020, 1022, 1023, 1025]
    return [category_map[cid] for cid in popular_ids if cid in category_map]


def _categories_from_db() -> list[dict]:
    rows = db.get_wb_categories()
    return [{"id": int(row["id"]), "name": str(row["name"]), "parent_id": row["parent_id"]} for row in rows]


@router.message(lambda m: m.text == "✨ Создать карточку WB")
async def start_generation(message: Message, state: FSMContext) -> None:
    user = message.from_user
    if not user:
        return
    row = db.get_user(user.id)
    if row and row["is_blocked"]:
        await message.answer("🚫 Ваш аккаунт заблокирован. Обратитесь в поддержку.")
        return
    price = int(db.get_setting("price_per_generation", "10"))
    limit = int(db.get_setting("max_generations_per_day", "20"))
    balance = db.get_balance(user.id)
    if balance < price:
        await message.answer("❌ Недостаточно кристаллов. Пополните баланс в разделе «💰 Купить кристаллы».")
        return
    if db.generations_count_for_today(user.id) >= limit:
        await message.answer("⚠️ Достигнут дневной лимит генераций. Попробуйте завтра.")
        return
    await state.clear()
    await state.set_state(FSMGeneration.waiting_for_name)
    await message.answer("📝 Введите название товара:")


@router.message(FSMGeneration.waiting_for_name)
async def step_name(message: Message, state: FSMContext) -> None:
    if not message.text:
        return
    await state.update_data(product_name=message.text.strip())
    await message.answer(
        "🖼 Отправьте основное фото товара (или «-», чтобы пропустить):",
    )
    await state.set_state(FSMGeneration.waiting_for_photo)


@router.message(FSMGeneration.waiting_for_photo, F.photo)
async def step_photo(message: Message, state: FSMContext) -> None:
    photo_file_id = message.photo[-1].file_id
    await state.update_data(photo_file_id=photo_file_id)
    await state.set_state(FSMGeneration.waiting_for_description)
    await message.answer("✍️ Введите описание товара (или отправьте «-», чтобы пропустить):")


@router.message(FSMGeneration.waiting_for_photo, F.text == "-")
async def step_photo_skip(message: Message, state: FSMContext) -> None:
    await state.update_data(photo_file_id="-")
    await state.set_state(FSMGeneration.waiting_for_description)
    await message.answer("✍️ Введите описание товара (или отправьте «-», чтобы пропустить):")


@router.message(FSMGeneration.waiting_for_photo)
async def step_photo_invalid(message: Message) -> None:
    await message.answer("Пожалуйста, отправьте фото или «-», чтобы пропустить этот шаг.")


@router.message(FSMGeneration.waiting_for_description)
async def step_description(message: Message, state: FSMContext) -> None:
    if not message.text:
        return
    description = "" if message.text.strip() == "-" else message.text.strip()
    await state.update_data(description=description)
    data = await state.get_data()
    categories = _categories_from_db() or await _load_categories()
    suggested: list[dict] = []
    try:
        ai_suggestions = await suggest_categories(data["product_name"], description or None)
        if ai_suggestions:
            category_by_name = {str(cat["name"]): cat for cat in categories}
            suggested = [category_by_name[name] for name in ai_suggestions if name in category_by_name][:5]
    except Exception:
        suggested = []

    if not suggested:
        suggested = _suggest_categories(data["product_name"], categories)[:5]

    await state.update_data(categories=categories, suggested_categories=suggested)
    await state.set_state(FSMGeneration.waiting_for_category)
    if suggested:
        await message.answer(
            "🤖 Подобрал категории через AI. Выберите подходящую:",
            reply_markup=suggested_categories_keyboard(suggested),
        )
    else:
        await message.answer(
            "📂 Выберите категорию товара:",
            reply_markup=categories_keyboard(categories, include_show_all=True),
        )


@router.callback_query(FSMGeneration.waiting_for_category, F.data == "cat:all")
async def show_all_categories(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.message:
        return
    data = await state.get_data()
    categories = data.get("categories", [])
    await callback.message.answer(
        "📚 Полный список категорий:",
        reply_markup=categories_keyboard(categories, include_show_all=False),
    )
    await callback.answer()


@router.callback_query(FSMGeneration.waiting_for_category, F.data.startswith("cat:"))
async def step_category(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.message:
        return
    category_id = int(callback.data.split(":")[1])
    await state.update_data(category_id=category_id)
    data = await state.get_data()
    await state.set_state(FSMGeneration.confirmation)
    await callback.message.answer(
        (
            "✅ Подтвердите генерацию карточки:\n\n"
            f"<b>Название:</b> {data['product_name']}\n"
            f"<b>Категория ID:</b> {category_id}\n"
            f"<b>Описание:</b> {data.get('description') or 'Авто'}\n\n"
            f"Будет списано {int(db.get_setting('price_per_generation', '10'))} кристаллов."
        ),
        parse_mode="HTML",
        reply_markup=generation_confirmation_keyboard(),
    )
    await callback.answer()


@router.callback_query(FSMGeneration.confirmation, F.data == "gen:cancel")
async def generation_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer("Отменено")
    if callback.message:
        await callback.message.answer("❌ Генерация отменена.")


@router.callback_query(FSMGeneration.confirmation, F.data == "gen:confirm")
async def generation_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    user = callback.from_user
    if not user or not callback.message:
        return
    row = db.get_user(user.id)
    if row and row["is_blocked"]:
        await callback.message.answer("🚫 Ваш аккаунт заблокирован. Обратитесь в поддержку.")
        await state.clear()
        await callback.answer()
        return
    data = await state.get_data()
    price = int(db.get_setting("price_per_generation", "10"))
    if db.get_balance(user.id) < price:
        await callback.message.answer("❌ Недостаточно кристаллов.")
        await state.clear()
        await callback.answer()
        return

    ok = db.change_balance(user.id, -price, "generation", stars_amount=0)
    if not ok:
        await callback.message.answer("❌ Не удалось списать кристаллы. Повторите попытку.")
        await state.clear()
        await callback.answer()
        return

    generated_description = (
        data["description"]
        or f"Название: {data['product_name']}. Категория: {data['category_id']}. Высокое качество и стиль."
    )
    # TODO: Here you can integrate OpenAI/YandexGPT/local LLM and generate rich specs.
    generated_characteristics = {
        "Материал": "Премиум",
        "Цвет": "Черный",
        "Назначение": "Повседневное",
    }
    categories = data.get("categories", [])
    category_name = next(
        (c.get("name", "") for c in categories if int(c.get("id", -1)) == int(data["category_id"])),
        f"Категория {data['category_id']}",
    )
    prompt = (
        f"{data['product_name']}, {category_name}, {generated_description}, "
        "high quality, detailed, professional product photo, white background, studio lighting"
    )
    progress_message = await callback.message.answer("🎨 Генерирую изображение через нейросеть... (до 15 секунд)")
    image_bytes = None
    try:
        image_bytes = await generate_image_via_pollinations(prompt=prompt, model="flux")
    finally:
        try:
            await progress_message.delete()
        except Exception:
            pass

    if image_bytes is None:
        await callback.message.answer("❌ Не удалось сгенерировать изображение. Попробуйте изменить описание и повторить.")
        await state.clear()
        await callback.answer()
        return

    sent_photo = await callback.message.answer_photo(
        photo=BufferedInputFile(image_bytes, filename="generated_product.png"),
        caption="🖼 Сгенерированное изображение товара",
    )
    image_link = sent_photo.photo[-1].file_id if sent_photo.photo else "-"
    result = {
        "title": data["product_name"],
        "description": generated_description,
        "characteristics": generated_characteristics,
        "image_link": image_link,
        "prompt": prompt,
    }
    generation_id = db.create_generation(
        user_id=user.id,
        product_name=data["product_name"],
        category_id=int(data["category_id"]),
        description=generated_description,
        photo_file_id=data["photo_file_id"],
        status="success",
        result_json=json.dumps(result, ensure_ascii=False),
    )
    await state.update_data(generation_id=generation_id)

    await callback.message.answer(
        (
            "🎉 <b>Карточка сгенерирована</b>\n\n"
            f"<b>Название:</b> {result['title']}\n"
            f"<b>Описание:</b> {result['description']}\n"
            f"<b>Характеристики:</b> {generated_characteristics}\n"
            f"<b>Изображение (file_id):</b> <code>{result['image_link']}</code>\n\n"
            f"ID генерации: <code>{generation_id}</code>"
        ),
        parse_mode="HTML",
    )
    payload = {
        "product_name": data["product_name"],
        "category_id": int(data["category_id"]),
        "description": generated_description,
        "image_file_id": image_link,
        "characteristics": generated_characteristics,
        "prompt": prompt,
    }
    await state.update_data(card_payload=payload)
    await callback.answer("Готово")
