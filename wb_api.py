from __future__ import annotations

import os
from typing import Any

import aiohttp

from config import WB_API_TOKEN


class WBApiError(Exception):
    pass


class WBApiClient:
    BASE_URL = "https://content-api.wildberries.ru"

    def __init__(self, token: str | None = None) -> None:
        token = token or WB_API_TOKEN or os.getenv("WB_API_TOKEN", "")
        self.token = token

    @property
    def headers(self) -> dict[str, str]:
        if not self.token:
            raise WBApiError("WB_API_TOKEN is not set")
        return {
            "Authorization": self.token,
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, path: str, **kwargs) -> Any:
        url = f"{self.BASE_URL}{path}"
        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.request(method, url, headers=self.headers, **kwargs) as response:
                payload = await response.json(content_type=None)
                if response.status >= 400:
                    raise WBApiError(f"WB API error {response.status}: {payload}")
                return payload

    async def get_categories(self) -> list[dict]:
        data = await self._request("GET", "/content/v2/categories")
        if isinstance(data, dict):
            return data.get("data", []) or data.get("categories", []) or []
        return data if isinstance(data, list) else []

    async def get_all_objects_page(self, limit: int = 1000, offset: int = 0) -> dict:
        return await self._request(
            "GET",
            f"/content/v2/object/all?limit={limit}&offset={offset}",
        )

    async def get_all_categories(self) -> list[dict]:
        offset = 0
        limit = 1000
        categories: list[dict] = []
        while True:
            page = await self.get_all_objects_page(limit=limit, offset=offset)
            data = page.get("data") if isinstance(page, dict) else None
            if not isinstance(data, list) or not data:
                break
            for item in data:
                if not isinstance(item, dict):
                    continue
                categories.append(
                    {
                        "id": item.get("subjectID") or item.get("id"),
                        "name": item.get("name") or item.get("subjectName"),
                        "parent_id": item.get("parentID") or item.get("parent_id"),
                    }
                )
            if len(data) < limit:
                break
            offset += limit
        return [c for c in categories if c.get("id") and c.get("name")]

    async def get_characteristics(self, subject_id: int) -> list[dict]:
        data = await self._request("GET", f"/content/v2/object/charcs/{subject_id}")
        if isinstance(data, dict):
            return data.get("data", []) or []
        return data if isinstance(data, list) else []

    async def get_limits(self) -> dict:
        data = await self._request("GET", "/content/v2/cards/limits")
        return data if isinstance(data, dict) else {"raw": data}

    async def upload_card(self, payload: dict) -> dict:
        data = await self._request("POST", "/content/v2/cards/upload", json=payload)
        return data if isinstance(data, dict) else {"raw": data}


def build_wb_card_payload(
    product_name: str,
    category_id: int,
    description: str,
    image_url: str,
) -> dict:
    return {
        "cards": [
            {
                "subjectID": category_id,
                "vendorCode": f"VC-{category_id}-{abs(hash(product_name)) % 100000}",
                "title": product_name,
                "description": description,
                "photos": [{"big": image_url}],
                "characteristics": [
                    {"name": "Бренд", "value": "NoName"},
                    {"name": "Комплектация", "value": "1 шт"},
                ],
            }
        ]
    }
