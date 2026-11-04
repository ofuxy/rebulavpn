from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
import sqlite3
import hashlib
from typing import Optional
import uuid
import telebot
from telebot import types  # <-- Импортируем типы для кнопок
import threading
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# НАСТРОЙКА TELEGRAM-БОТА
# ==========================================
BOT_TOKEN = "9151293076:AAGBVkPdzSLc9jSoAA7r2Z9eoGs4sRN0VVg" 
bot = telebot.TeleBot(BOT_TOKEN)

# Главное меню с кнопками
def get_main_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_profile = types.InlineKeyboardButton("👤 Мой профиль", callback_data="profile")
    btn_connect = types.InlineKeyboardButton("⚡ Подключиться (скачать конфиг)", callback_data="connect")
    btn_help = types.InlineKeyboardButton("❓ Помощь", callback_data="help")
    markup.add(btn_profile, btn_connect, btn_help)
    return markup

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    text = (
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        "Добро пожаловать в **NebulaVPN**.\n"
        "Выбери нужное действие на клавиатуре ниже:"
    )
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=get_main_menu())

# Обработчик команды /menu (если пользователь её напишет)
@bot.message_handler(commands=['menu'])
def send_menu(message):
    bot.send_message(message.chat.id, "Главное меню:", reply_markup=get_main_menu())

# --- ОБРАБОТКА НАЖАТИЙ НА КНОПКИ ---
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    try:
        if call.message:
            if call.data == "profile":
                # Убираем "часики" загрузки на кнопке
                bot.answer_callback_query(call.id)
                text = (
                    f"👤 **Твой профиль:**\n"
                    f"ID: `{call.from_user.id}`\n"
                    f"Имя: {call.from_user.first_name}\n"
                    f"Тариф: Free (Демо)\n"
                    f"Статус: Активен"
                )
                bot.send_message(call.message.chat.id, text, parse_mode='Markdown')

            elif call.data == "connect":
                bot.answer_callback_query(call.id, "Генерирую конфиг...")
                send_config_file(call.message.chat.id, call.from_user.id)

            elif call.data == "help":
                bot.answer_callback_query(call.id)
                text = (
                    "📖 **Инструкция:**\n"
                    "1. Нажми кнопку 'Подключиться'.\n"
                    "2. Бот пришлет файл `.conf`.\n"
                    "3. Скачай приложение **WireGuard** (в App Store или Google Play).\n"
                    "4. В приложении нажми '+' -> 'Импорт из файла' и выбери скачанный конфиг.\n"
                    "5. Включи туннель и пользуйся!"
                )
                bot.send_message(call.message.chat.id, text, parse_mode='Markdown')
    except Exception as e:
        print(f"Callback error: {e}")

# Функция генерации и отправки конфига
def send_config_file(chat_id, user_id):
    fake_key = hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()[:43] + "="
    config_text = f"""[Interface]
PrivateKey = {fake_key}
Address = 10.66.66.2/32
DNS = 1.1.1.1, 8.8.8.8

[Peer]
PublicKey = xTIB3dE9pX2sZ4y8w7v6u5t4s3r2q1p0o9n8m7l6k5j4h3g2f1=
AllowedIPs = 0.0.0.0/0
Endpoint = 127.0.0.1:51820

# Telegram Config for {user_id}
"""
    bot.send_document(chat_id, config_text.encode('utf-8'), visible_file_name="nebulavpn.conf", caption="📥 Твой конфиг готов! Импортируй его в WireGuard.")

# Старая текстовая команда (оставим на всякий случай)
@bot.message_handler(commands=['config'])
def send_config_cmd(message):
    send_config_file(message.chat.id, message.from_user.id)

# Запускаем бота в отдельном потоке
def run_bot():
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            print(f"Bot error: {e}")
            time.sleep(5)

threading.Thread(target=run_bot, daemon=True).start()
# ==========================================

# --- РАБОТА С БАЗОЙ ДАННЫХ (без изменений) ---
def get_db():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.on_event("startup")
def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS users
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     email TEXT UNIQUE NOT NULL,
                     password_hash TEXT NOT NULL)''')
    conn.commit()
    conn.close()

def hash_password(password: str):
    return hashlib.sha256(password.encode()).hexdigest()

class UserAuth(BaseModel):
    email: str
    password: str
    mode: Optional[str] = "login"

@app.get("/")
def read_root():
    return {"status": "Server with Bot and Menu is running!"}

@app.post("/api/auth")
def auth_user(user: UserAuth):
    conn = get_db()
    cursor = conn.cursor()
    password_hash = hash_password(user.password)

    if user.mode == "register":
        try:
            cursor.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)", (user.email, password_hash))
            conn.commit()
            return {"status": "success", "message": f"Аккаунт {user.email} создан!"}
        except sqlite3.IntegrityError:
            return {"status": "error", "message": "Этот email уже зарегистрирован."}
        finally:
            conn.close()
    else:
        cursor.execute("SELECT password_hash FROM users WHERE email = ?", (user.email,))
        row = cursor.fetchone()
        conn.close()

        if row:
            if row["password_hash"] == password_hash:
                return {"status": "success", "message": f"С возвращением!"}
            else:
                return {"status": "error", "message": "Неверный пароль."}
        else:
            return {"status": "error", "message": "Пользователь не найден."}

@app.get("/api/vpn/config")
def get_vpn_config(email: str):
    fake_key = hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()[:43] + "="
    config_text = f"""[Interface]
PrivateKey = {fake_key}
Address = 10.66.66.2/32
DNS = 1.1.1.1, 8.8.8.8

[Peer]
PublicKey = xTIB3dE9pX2sZ4y8w7v6u5t4s3r2q1p0o9n8m7l6k5j4h3g2f1=
AllowedIPs = 0.0.0.0/0
Endpoint = 127.0.0.1:51820

# Web Config for {email}
"""
    return PlainTextResponse(config_text, headers={
        "Content-Disposition": f"attachment; filename=nebulavpn_{email.split('@')[0]}.conf"
    })

@app.get("/api/vpn/stats")
def get_vpn_stats():
    return {
        "ip": "127.0.0.1",
        "country": "Demo",
        "ping": "10 ms",
        "download": "0 GB",
        "upload": "0 GB"
}
