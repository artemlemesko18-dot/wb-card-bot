import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from config import DB_PATH, MAX_GENERATIONS_PER_DAY, PRICE_PER_GENERATION, STARS_RATE


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path: str = DB_PATH) -> None:
        self.path = path
        self._init_db()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    balance INTEGER NOT NULL DEFAULT 0,
                    is_blocked INTEGER NOT NULL DEFAULT 0,
                    registered_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS generations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    product_name TEXT NOT NULL,
                    category_id INTEGER NOT NULL,
                    description TEXT,
                    photo_file_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    result_json TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                );

                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    amount INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    stars_amount INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                );

                CREATE TABLE IF NOT EXISTS admin_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS wb_categories (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    parent_id INTEGER
                );
                """
            )

            defaults = {
                "price_per_generation": str(PRICE_PER_GENERATION),
                "stars_rate": str(STARS_RATE),
                "max_generations_per_day": str(MAX_GENERATIONS_PER_DAY),
            }
            for key, value in defaults.items():
                conn.execute(
                    "INSERT OR IGNORE INTO admin_settings(key, value) VALUES(?, ?)",
                    (key, value),
                )

    def replace_wb_categories(self, categories: list[dict[str, Any]]) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM wb_categories")
            conn.executemany(
                "INSERT INTO wb_categories(id, name, parent_id) VALUES(?, ?, ?)",
                [
                    (int(item["id"]), str(item["name"]), item.get("parent_id"))
                    for item in categories
                    if item.get("id") is not None and item.get("name")
                ],
            )

    def get_wb_categories(self) -> list[sqlite3.Row]:
        with self._connect() as conn:
            rows = conn.execute("SELECT id, name, parent_id FROM wb_categories ORDER BY name").fetchall()
            return list(rows)

    def get_setting(self, key: str, default: Any = None) -> Any:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM admin_settings WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else default

    def set_setting(self, key: str, value: Any) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO admin_settings(key, value) VALUES(?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, str(value)),
            )

    def upsert_user(self, user_id: int, username: str | None, first_name: str | None) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO users(user_id, username, first_name, registered_at)
                VALUES(?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name
                """,
                (user_id, username, first_name, utc_now()),
            )

    def get_user(self, user_id: int) -> sqlite3.Row | None:
        with self._connect() as conn:
            return conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()

    def list_users(self, limit: int = 50, offset: int = 0) -> list[sqlite3.Row]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM users ORDER BY registered_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
            return list(rows)

    def set_user_blocked(self, user_id: int, blocked: bool) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE users SET is_blocked = ? WHERE user_id = ?", (1 if blocked else 0, user_id))

    def get_balance(self, user_id: int) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)).fetchone()
            return int(row["balance"]) if row else 0

    def change_balance(self, user_id: int, amount: int, tx_type: str, stars_amount: int = 0) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if not row:
                return False
            new_balance = int(row["balance"]) + amount
            if new_balance < 0:
                return False
            conn.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
            conn.execute(
                """
                INSERT INTO transactions(user_id, amount, type, stars_amount, created_at)
                VALUES(?, ?, ?, ?, ?)
                """,
                (user_id, amount, tx_type, stars_amount, utc_now()),
            )
            return True

    def create_generation(
        self,
        user_id: int,
        product_name: str,
        category_id: int,
        description: str | None,
        photo_file_id: str,
        status: str = "pending",
        result_json: str | None = None,
    ) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO generations(
                    user_id, product_name, category_id, description, photo_file_id, status, result_json, created_at
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, product_name, category_id, description, photo_file_id, status, result_json, utc_now()),
            )
            return int(cur.lastrowid)

    def update_generation_status(self, generation_id: int, status: str, result_json: str | None = None) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE generations SET status = ?, result_json = ? WHERE id = ?",
                (status, result_json, generation_id),
            )

    def get_generation(self, generation_id: int) -> sqlite3.Row | None:
        with self._connect() as conn:
            return conn.execute("SELECT * FROM generations WHERE id = ?", (generation_id,)).fetchone()

    def list_generations(self, limit: int = 50, offset: int = 0) -> list[sqlite3.Row]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM generations ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
            return list(rows)

    def generations_count_for_today(self, user_id: int) -> int:
        today_prefix = datetime.now(timezone.utc).date().isoformat()
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS cnt FROM generations
                WHERE user_id = ? AND created_at LIKE ? || '%'
                """,
                (user_id, today_prefix),
            ).fetchone()
            return int(row["cnt"]) if row else 0

    def get_stats(self) -> dict[str, int]:
        with self._connect() as conn:
            users = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
            generations = conn.execute("SELECT COUNT(*) AS c FROM generations").fetchone()["c"]
            sold_crystals = conn.execute(
                "SELECT COALESCE(SUM(amount), 0) AS c FROM transactions WHERE type = 'purchase'"
            ).fetchone()["c"]
            revenue = conn.execute(
                "SELECT COALESCE(SUM(stars_amount), 0) AS c FROM transactions WHERE type = 'purchase'"
            ).fetchone()["c"]
            return {
                "users": int(users),
                "generations": int(generations),
                "sold_crystals": int(sold_crystals),
                "revenue_stars": int(revenue),
            }
