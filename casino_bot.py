import os
import random
import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv

# Настройки
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Константы
SLOT_SYMBOLS = ["🍒", "🍋", "🍊", "🍇", "🔔", "7️⃣"]
ROULETTE_NUMBERS = list(range(0, 37))
ANIMATION_STEPS = 8
ANIMATION_DELAY = 0.2
GAMES_FOR_ADS = 6  # Количество игр перед показом рекламы
AD_MESSAGE = (
    "🔥 Сегодня тебе везет! Переходи на полную версию для вывода средств:\n"
    "https://1wrjmw.com/?open=register&p=q8uw"
)

# Инициализация БД
async def init_db():
    async with aiosqlite.connect("casino.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                credits INTEGER DEFAULT 1000,
                slots_played INTEGER DEFAULT 0,
                roulette_played INTEGER DEFAULT 0
            )
        """)
        await db.commit()

# Клавиатура
def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎰 Слоты (10 кредитов)"), KeyboardButton(text="🎲 Рулетка (20 кредитов)")],
            [KeyboardButton(text="💰 Мой баланс")]
        ],
        resize_keyboard=True
    )

# Анимация слотов
async def animate_slots(message: types.Message, final_result):
    for i in range(ANIMATION_STEPS):
        frame = [random.choice(SLOT_SYMBOLS) for _ in range(3)]
        await message.edit_text(f"🎰 Крутим...\n{' | '.join(frame)}")
        await asyncio.sleep(ANIMATION_DELAY)
    await message.edit_text(f"🎰 {' | '.join(final_result)}")

# Анимация рулетки
async def animate_roulette(message: types.Message, final_number):
    for i in range(ANIMATION_STEPS):
        frame_num = random.choice(ROULETTE_NUMBERS)
        color = get_color_for_number(frame_num)
        await message.edit_text(f"🎲 Крутится...\n{color} {frame_num}")
        await asyncio.sleep(ANIMATION_DELAY)
    final_color = get_color_for_number(final_number)
    await message.edit_text(f"🎲 {final_color} {final_number}")

def get_color_for_number(number):
    if number == 0:
        return "🟢"
    elif (1 <= number <= 10 and number % 2 == 1) or (11 <= number <= 18 and number % 2 == 0) or (19 <= number <= 28 and number % 2 == 1) or (29 <= number <= 36 and number % 2 == 0):
        return "🔴"
    else:
        return "⚫"

async def check_for_advertisement(user_id: int, game_type: str, message: types.Message):
    """Проверяет, нужно ли показать рекламное сообщение"""
    async with aiosqlite.connect("casino.db") as db:
        # Получаем количество сыгранных игр
        if game_type == "slots":
            query = "SELECT slots_played FROM players WHERE user_id = ?"
            update_query = "UPDATE players SET slots_played = slots_played + 1 WHERE user_id = ?"
        else:
            query = "SELECT roulette_played FROM players WHERE user_id = ?"
            update_query = "UPDATE players SET roulette_played = roulette_played + 1 WHERE user_id = ?"
        
        async with db.execute(query, (user_id,)) as cursor:
            games_played = (await cursor.fetchone())[0]
        
        # Обновляем счетчик игр
        await db.execute(update_query, (user_id,))
        await db.commit()
        
        # Проверяем, нужно ли показать рекламу
        if games_played > 0 and games_played % GAMES_FOR_ADS == 0:
            await message.answer(AD_MESSAGE)

# Обработчики
@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or str(user_id)

    async with aiosqlite.connect("casino.db") as db:
        async with db.execute("SELECT 1 FROM players WHERE user_id = ?", (user_id,)) as cursor:
            if not await cursor.fetchone():
                await db.execute(
                    "INSERT INTO players (user_id, username) VALUES (?, ?)",
                    (user_id, username)
                )
                await db.commit()
                await message.answer(
                    "🎉 Добро пожаловать! Вам начислено 1000 кредитов.",
                    reply_markup=get_main_keyboard()
                )
            else:
                await message.answer("🔄 С возвращением!", reply_markup=get_main_keyboard())

@dp.message(lambda m: m.text == "🎰 Слоты (10 кредитов)")
async def play_slots(message: types.Message):
    user_id = message.from_user.id
    cost = 10

    async with aiosqlite.connect("casino.db") as db:
        async with db.execute("SELECT credits FROM players WHERE user_id = ?", (user_id,)) as cursor:
            credits = (await cursor.fetchone())[0]

        if credits < cost:
            await message.answer("❌ Недостаточно кредитов!")
            return

        msg = await message.answer("🎰 Подготовка к игре...")
        result = [random.choice(SLOT_SYMBOLS) for _ in range(3)]
        await animate_slots(msg, result)

        if result[0] == result[1] == result[2]:
            win = 50
        elif result[0] == result[1] or result[1] == result[2]:
            win = 20
        else:
            win = -cost

        await db.execute(
            "UPDATE players SET credits = credits + ? WHERE user_id = ?",
            (win, user_id)
        )
        await db.commit()

        if win > 0:
            await message.answer(
                f"🎉 <b>Вы выиграли {win} кредитов!</b>\n"
                f"💎 Комбинация: {' | '.join(result)}",
                parse_mode=ParseMode.HTML
            )
        else:
            await message.answer(
                f"😢 Вы проиграли {abs(win)} кредитов\n"
                f"🌀 Комбинация: {' | '.join(result)}"
            )
        
        # Проверка на показ рекламы
        await check_for_advertisement(user_id, "slots", message)

@dp.message(lambda m: m.text == "🎲 Рулетка (20 кредитов)")
async def play_roulette(message: types.Message):
    user_id = message.from_user.id
    cost = 20

    async with aiosqlite.connect("casino.db") as db:
        async with db.execute("SELECT credits FROM players WHERE user_id = ?", (user_id,)) as cursor:
            credits = (await cursor.fetchone())[0]

        if credits < cost:
            await message.answer("❌ Недостаточно кредитов!")
            return

        msg = await message.answer("🎲 Запускаем рулетку...")
        number = random.randint(0, 36)
        await animate_roulette(msg, number)

        color = get_color_for_number(number)
        if number == 0:
            win = cost * 35
        elif color == "🔴":
            win = cost * 1.5
        else:
            win = -cost

        await db.execute(
            "UPDATE players SET credits = credits + ? WHERE user_id = ?",
            (win, user_id)
        )
        await db.commit()

        if win > 0:
            await message.answer(
                f"🎉 <b>Вы выиграли {win} кредитов!</b>\n"
                f"🎲 Результат: {color} {number}",
                parse_mode=ParseMode.HTML
            )
        else:
            await message.answer(
                f"😢 Вы проиграли {abs(win)} кредитов\n"
                f"🎲 Результат: {color} {number}"
            )
        
        # Проверка на показ рекламы
        await check_for_advertisement(user_id, "roulette", message)

@dp.message(lambda m: m.text == "💰 Мой баланс")
async def show_balance(message: types.Message):
    user_id = message.from_user.id

    async with aiosqlite.connect("casino.db") as db:
        async with db.execute("SELECT credits FROM players WHERE user_id = ?", (user_id,)) as cursor:
            credits = (await cursor.fetchone())[0]

    await message.answer(f"💰 Ваш баланс: {credits} кредитов")

# Запуск бота
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    print("🎰 Казино-бот запускается...")
    asyncio.run(main())