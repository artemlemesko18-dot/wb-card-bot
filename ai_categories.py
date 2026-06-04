import json

from openai import AsyncOpenAI

from config import OPENAI_API_KEY, OPENAI_MODEL
from services import db


async def suggest_categories(product_name: str, description: str | None = None) -> list[str]:
    categories = db.get_wb_categories()
    if not categories:
        return []

    category_names = [str(row["name"]) for row in categories]
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    user_prompt = (
        f"Название товара: {product_name}\n"
        f"Описание: {description or '-'}\n\n"
        "Список категорий:\n"
        + "\n".join(f"- {name}" for name in category_names)
    )
    completion = await client.chat.completions.create(
        model=OPENAI_MODEL,
        temperature=0.1,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "Ты помощник селлера Wildberries. На основе названия и описания товара выбери "
                    "3-5 наиболее подходящих категорий из предоставленного списка. "
                    "Верни только JSON-объект формата {\"categories\":[\"...\"]}."
                ),
            },
            {"role": "user", "content": user_prompt},
        ],
    )
    content = completion.choices[0].message.content or "{}"
    data = json.loads(content)
    suggested = data.get("categories", [])
    if not isinstance(suggested, list):
        return []
    known = set(category_names)
    result: list[str] = []
    for item in suggested:
        if isinstance(item, str) and item in known and item not in result:
            result.append(item)
        if len(result) >= 5:
            break
    return result
