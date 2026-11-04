from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import hashlib
from typing import Optional

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- РАБОТА С БАЗОЙ ДАННЫХ ---
def get_db():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn

# Создаем таблицу при запуске сервера
@app.on_event("startup")
def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS users
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     email TEXT UNIQUE NOT NULL,
                     password_hash TEXT NOT NULL)''')
    conn.commit()
    conn.close()

# Хэшируем пароль (превращаем в шифр)
def hash_password(password: str):
    return hashlib.sha256(password.encode()).hexdigest()


# --- МОДЕЛИ ДАННЫХ ---
class UserAuth(BaseModel):
    email: str
    password: str
    mode: Optional[str] = "login" # Сайт будет передавать 'login' или 'register'


# --- ЭНДПОИНТЫ ---
@app.get("/")
def read_root():
    return {"status": "Server with Database is running!"}

@app.post("/api/auth")
def auth_user(user: UserAuth):
    conn = get_db()
    cursor = conn.cursor()
    password_hash = hash_password(user.password)

    if user.mode == "register":
        try:
            # Пытаемся добавить нового юзера
            cursor.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)", (user.email, password_hash))
            conn.commit()
            return {"status": "success", "message": f"Аккаунт {user.email} создан и сохранен в базе!"}
        except sqlite3.IntegrityError:
            # Если такой email уже есть (UNIQUE constraint failed)
            return {"status": "error", "message": "Этот email уже зарегистрирован. Попробуй войти."}
        finally:
            conn.close()
            
    else: # Если mode == 'login'
        cursor.execute("SELECT password_hash FROM users WHERE email = ?", (user.email,))
        row = cursor.fetchone()
        conn.close()

        if row:
            if row["password_hash"] == password_hash:
                return {"status": "success", "message": f"С возвращением, {user.email}!"}
            else:
                return {"status": "error", "message": "Неверный пароль."}
        else:
            return {"status": "error", "message": "Пользователь не найден. Сначала зарегистрируйся."}
