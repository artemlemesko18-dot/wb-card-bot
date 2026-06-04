from database import Database
from wb_api import WBApiClient


db = Database()
wb_client = WBApiClient()


async def refresh_wb_categories_cache() -> int:
    categories = await wb_client.get_all_categories()
    if not categories:
        return 0
    db.replace_wb_categories(categories)
    return len(categories)
