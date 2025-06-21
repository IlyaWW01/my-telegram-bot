import os
import random
import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv

# Загружаем .env
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# Инициализируем бота
bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# База данных
DB_NAME = "casino.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                credits INTEGER DEFAULT 1000,
                slots_played INTEGER DEFAULT 0,
                roulette_played INTEGER DEFAULT 0
            )
        ''')
        await db.commit()

def get_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎰 Слоты (10 кредитов)"), 
             KeyboardButton(text="🎲 Рулетка (20 кредитов)")],
            [KeyboardButton(text="💰 Мой баланс")]
        ],
        resize_keyboard=True
    )

@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "unknown"

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT * FROM players WHERE user_id = ?", (user_id,)) as cursor:
            data = await cursor.fetchone()
        if not data:
            await db.execute("INSERT INTO players (user_id, username) VALUES (?, ?)", (user_id, username))
            await db.commit()
            await message.answer("🎉 Добро пожаловать! Вам начислено 1000 кредитов.", reply_markup=get_keyboard())
        else:
            await message.answer("🔄 С возвращением!", reply_markup=get_keyboard())

@dp.message(lambda m: m.text.startswith('🎰'))
async def slots(message: types.Message):
    user_id = message.from_user.id

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT credits, slots_played FROM players WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                await message.answer("Вы ещё не начали игру! Напишите /start")
                return

            credits, played = row

        if played >= 5:
            await message.answer("🔥 Вы исчерпали лимит! Переходите на полную версию:\nhttps://example.com")
            return

        if credits < 10:
            await message.answer("❌ Недостаточно кредитов!")
            return

        result = [random.randint(1, 5) for _ in range(3)]
        if result[0] == result[1] == result[2]:
            win = 50
        elif result[0] == result[1] or result[1] == result[2]:
            win = 20
        else:
            win = -10

        await db.execute(
            "UPDATE players SET credits = credits + ?, slots_played = slots_played + 1 WHERE user_id = ?",
            (win, user_id)
        )
        await db.commit()

    await message.answer(
        f"🎰 {' | '.join(map(str, result))}\n"
        f"{'✅ Выигрыш' if win > 0 else '❌ Проигрыш'}: {abs(win)} кредитов"
    )

@dp.message(lambda m: m.text.startswith('💰'))
async def balance(message: types.Message):
    user_id = message.from_user.id

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT credits, slots_played, roulette_played FROM players WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                await message.answer("Вы ещё не начали игру! Напишите /start")
                return
            credits, slots, roulette = row

    await message.answer(f"💰 Баланс: {credits}\n🎰 Слотов сыграно: {slots}/5\n🎲 Рулеток сыграно: {roulette}/5")

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
