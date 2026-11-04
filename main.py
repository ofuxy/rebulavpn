from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Эта штука нужна, чтобы твой сайт с GitHub мог общаться с этим сервером
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Описываем, какие данные мы ждем от сайта (почту и пароль)
class UserAuth(BaseModel):
    email: str
    password: str

# Главная страница сервера (проверка, что он жив)
@app.get("/")
def read_root():
    return {"status": "Server is running!"}

# Эндпоинт (ручка), куда будет стучаться наш сайт при регистрации/входе
@app.post("/api/auth")
def auth_user(user: UserAuth):
    # ТУТ ПОТОМ БУДЕТ БАЗА ДАННЫХ, А ПОКА ПРОСТО ВЫВОДИМ В КОНСОЛЬ
    print(f"Пришла заявка от: {user.email}")
    
    # Отвечаем сайту, что всё ок
    return {
        "status": "success",
        "message": f"Привет, {user.email}! Твой аккаунт создан (пока в тестовом режиме)."
}
