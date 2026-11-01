# =============================================
# Пам'ять Тето
# =============================================
import sqlite3

# Ініціалізація бази даних
# Файл teto_memory.db створюється поруч із main.py, якщо його ще немає.
db_conn = sqlite3.connect('teto_memory.db')
db_cursor = db_conn.cursor()

db_cursor.execute('''
    CREATE TABLE IF NOT EXISTS chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        role TEXT,
        content TEXT
    )
''')

db_cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_settings (
        user_id INTEGER PRIMARY KEY,
        gender TEXT
    )
''')

db_conn.commit()

def save_message(user_id, role, content):
    db_cursor.execute('INSERT INTO chat_history (user_id, role, content) VALUES (?, ?, ?)', (user_id, role, content))
    db_conn.commit()

def load_history(user_id, limit=5):
    db_cursor.execute('''
        SELECT role, content FROM (
            SELECT role, content, id FROM chat_history
            WHERE user_id = ?
            ORDER BY id DESC LIMIT ?
        ) ORDER BY id ASC
    ''', (user_id, limit))
    return [{"role": r, "parts": [c]} for r, c in db_cursor.fetchall()]

def save_user_gender(user_id, gender):
    db_cursor.execute('INSERT OR REPLACE INTO user_settings (user_id, gender) VALUES (?, ?)', (user_id, gender))
    db_conn.commit()

def load_user_gender(user_id):
    db_cursor.execute('SELECT gender FROM user_settings WHERE user_id = ?', (user_id,))
    result = db_cursor.fetchone()
    return result[0] if result else None
