# =============================================
# Пам'ять Тето
# =============================================
import sqlite3

db_conn = sqlite3.connect("teto_memory.db")
db_cursor = db_conn.cursor()

# Історія повідомлень
db_cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        role TEXT,
        content TEXT
    )
""")

# Налаштування користувачів
db_cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_settings (
        user_id INTEGER PRIMARY KEY,
        gender TEXT,
        city TEXT
    )
""")

# Міграція старої БД: додаємо city, якщо його ще немає
db_cursor.execute("PRAGMA table_info(user_settings)")
columns = [column[1] for column in db_cursor.fetchall()]

if "city" not in columns:
    db_cursor.execute("ALTER TABLE user_settings ADD COLUMN city TEXT")

db_conn.commit()


# =============================================
# Історія повідомлень
# =============================================

def save_message(user_id, role, content):
    db_cursor.execute(
        "INSERT INTO chat_history (user_id, role, content) VALUES (?, ?, ?)",
        (user_id, role, content)
    )
    db_conn.commit()


def load_history(user_id, limit=5):
    db_cursor.execute("""
        SELECT role, content FROM (
            SELECT role, content, id FROM chat_history
            WHERE user_id = ?
            ORDER BY id DESC LIMIT ?
        ) ORDER BY id ASC
    """, (user_id, limit))

    return [
        {"role": role, "parts": [content]}
        for role, content in db_cursor.fetchall()
    ]


# =============================================
# Стать користувача
# =============================================

def save_user_gender(user_id, gender):
    db_cursor.execute("""
        INSERT INTO user_settings (user_id, gender)
        VALUES (?, ?)
        ON CONFLICT(user_id)
        DO UPDATE SET gender = excluded.gender
    """, (user_id, gender))

    db_conn.commit()


def load_user_gender(user_id):
    db_cursor.execute(
        "SELECT gender FROM user_settings WHERE user_id = ?",
        (user_id,)
    )

    result = db_cursor.fetchone()
    return result[0] if result else None


# =============================================
# Місто користувача
# =============================================

def save_user_city(user_id, city):
    db_cursor.execute("""
        INSERT INTO user_settings (user_id, city)
        VALUES (?, ?)
        ON CONFLICT(user_id)
        DO UPDATE SET city = excluded.city
    """, (user_id, city))

    db_conn.commit()


def load_user_city(user_id):
    db_cursor.execute(
        "SELECT city FROM user_settings WHERE user_id = ?",
        (user_id,)
    )

    result = db_cursor.fetchone()
    return result[0] if result else None