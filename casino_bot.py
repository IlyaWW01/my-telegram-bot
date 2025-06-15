import os
import random
import sqlite3
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.enums import ParseMode
import asyncio

# Загрузка токена
load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')

if not TOKEN:
    raise ValueError("Токен не найден! Проверьте .env файл")

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# Подключение к базе данных
conn = sqlite3.connect('casino.db')
cursor = conn.cursor()

# Создаем таблицу для игроков
cursor.execute('''
CREATE TABLE IF NOT EXISTS players (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    credits INTEGER DEFAULT 1000
)
''')
conn.commit()

# Клавиатура с играми
games_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎰 Слоты (10 кредитов)"), KeyboardButton(text="🎲 Рулетка (20 кредитов)")],
        [KeyboardButton(text="♠️ Блэкджек (50 кредитов)"), KeyboardButton(text="💰 Мой баланс")]
    ],
    resize_keyboard=True
)

# Старт
@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username

    cursor.execute('SELECT credits FROM players WHERE user_id = ?', (user_id,))
    if cursor.fetchone() is None:
        cursor.execute('INSERT INTO players (user_id, username, credits) VALUES (?, ?, 1000)', (user_id, username))
        conn.commit()
        await message.answer("🎉 Добро пожаловать в казино! Вам начислено 1000 кредитов.", reply_markup=games_keyboard)
    else:
        await message.answer("🔄 Возвращаем вас в игру!", reply_markup=games_keyboard)

# Остальные обработчики (слоты, рулетка и т.д.) остаются без изменений
# ...

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())