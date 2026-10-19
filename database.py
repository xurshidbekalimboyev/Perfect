from datetime import datetime
import sqlite3
from config import DB_NAME


def get_connection():
    return sqlite3.connect(DB_NAME)


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Foydalanuvchilar jadvali
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            username TEXT,
            language TEXT DEFAULT 'uz',
            is_banned INTEGER DEFAULT 0,
            joined_at TEXT
        )
    """
    )

    # Guruhlar jadvali
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS groups (
            chat_id INTEGER PRIMARY KEY,
            title TEXT,
            joined_at TEXT
        )
    """
    )

    conn.commit()
    conn.close()


def add_or_update_user(user_id: int, full_name: str, username: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    exists = cur.fetchone()

    if not exists:
        cur.execute(
            """
            INSERT INTO users (user_id, full_name, username, language, is_banned, joined_at)
            VALUES (?, ?, ?, 'uz', 0, ?)
        """,
            (user_id, full_name, username, datetime.now().isoformat()),
        )
    else:
        cur.execute(
            """
            UPDATE users SET full_name = ?, username = ? WHERE user_id = ?
        """,
            (full_name, username, user_id),
        )

    conn.commit()
    conn.close()


def set_user_language(user_id: int, lang: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET language = ? WHERE user_id = ?", (lang, user_id)
    )
    conn.commit()
    conn.close()


def get_user_language(user_id: int) -> str:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
    res = cur.fetchone()
    conn.close()
    return res[0] if res and res[0] else "uz"


def is_user_banned(user_id: int) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
    res = cur.fetchone()
    conn.close()
    return bool(res and res[0] == 1)


def set_ban_status(user_id: int, status: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET is_banned = ? WHERE user_id = ?", (status, user_id)
    )
    conn.commit()
    conn.close()


def add_group(chat_id: int, title: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT chat_id FROM groups WHERE chat_id = ?", (chat_id,))
    exists = cur.fetchone()
    if not exists:
        cur.execute(
            """
            INSERT INTO groups (chat_id, title, joined_at)
            VALUES (?, ?, ?)
        """,
            (chat_id, title, datetime.now().isoformat()),
        )
    conn.commit()
    conn.close()


def remove_group(chat_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM groups WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()


def get_statistics():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM groups")
    total_groups = cur.fetchone()[0]

    cur.execute(
        "SELECT language, COUNT(*) FROM users GROUP BY language"
    )
    lang_stats = dict(cur.fetchall())
    conn.close()
    return total_users, total_groups, lang_stats


def get_broadcast_list(target: str):
    conn = get_connection()
    cur = conn.cursor()
    targets = []
    if target in ["users", "all"]:
        cur.execute("SELECT user_id FROM users WHERE is_banned = 0")
        targets.extend([r[0] for r in cur.fetchall()])
    if target in ["groups", "all"]:
        cur.execute("SELECT chat_id FROM groups")
        targets.extend([r[0] for r in cur.fetchall()])
    conn.close()
    return list(set(targets))
