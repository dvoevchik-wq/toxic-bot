import asyncio
import random
import datetime
import aiosqlite

from aiogram import Bot, Dispatcher
from aiogram.types import Message

TOKEN = "8257531005:AAFiayYvnGVtFEq6eAuhBwxL0-wLbL0jVDA"
CHAT_ID = -1003620457558

bot = Bot(TOKEN)
dp = Dispatcher()

PROMISE_WORDS = ["ща", "сек", "выхожу", "сейчас", "потом"]
QUESTION_WORDS = ["кто", "что", "почему", "зачем", "как", "когда", "где", "сколько"]

SHORT_ANSWERS = [
    "да", "нет", "возможно", "скорее да", "скорее нет",
    "сомневаюсь", "вряд ли", "логично", "походу да",
    "не уверен", "как пойдёт",
]

USER_CONTEXT = {}
LAST_REPLY_TIME = {}

STYLE_PHRASES = {
    "promise": [
        "Опять обещание. История не на твоей стороне.",
        "Ты это уже говорил.",
        "Я записал. Чтобы потом напомнить.",
        "Обещал — исчез.",
        "Ну да, конечно.",
        "Ща — это когда никогда.",
        "Ты мастер жанра «потом».",
        "Сказал — ушёл в туман.",
    ],
    "silent": [
        "С возвращением. Мы не заметили.",
        "Молчание — твой вклад.",
        "Лучше бы дальше молчал.",
        "Это и было твоё мнение?",
        "Редкий кадр.",
        "Ты снова в эфире.",
    ],
    "talker": [
        "Слов много. Смысл потерялся.",
        "Можно было короче. И молча.",
        "Ты опять пишешь. Зря.",
        "Монолог засчитан.",
        "Можно было оформить в книгу.",
        "Ты пишешь быстрее, чем думаешь.",
    ],
    "smartass": [
        "Уверенно. И неверно.",
        "Мысль есть. Проверку не прошла.",
        "Ты сам в это веришь?",
        "Звучит умно. Не является.",
        "Самоуверенность есть, точности нет.",
        "Ты споришь с фактами.",
    ],
    "chaos": [
        "Контекст не выжил.",
        "Это было лишним.",
        "Я не понял. Ты тоже.",
        "Смысл погиб по дороге.",
        "Сообщение в стиле «что».",
        "Переведи с хаоса на русский.",
    ]
}

GENERIC_PHRASES = [
    "Сомнительно.",
    "Продолжай, я записываю.",
    "Это многое объясняет.",
    "Хорошая попытка.",
    "Ну допустим.",
    "Я делаю вид, что понял.",
]

DB = "bot.db"


async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            style TEXT,
            promise INTEGER DEFAULT 0,
            talker INTEGER DEFAULT 0,
            smartass INTEGER DEFAULT 0,
            silent INTEGER DEFAULT 0,
            chaos INTEGER DEFAULT 0
        )
        """)
        await db.commit()


def update_context(uid, text):
    USER_CONTEXT.setdefault(uid, []).append(text)
    if len(USER_CONTEXT[uid]) > 5:
        USER_CONTEXT[uid].pop(0)


def analyze_logic(uid):
    msgs = USER_CONTEXT.get(uid, [])
    if len(msgs) < 2:
        return None

    last = msgs[-1]
    prev = msgs[-2]

    if prev == last:
        return "Ты это уже говорил. Повтор — не аргумент."

    if "не" in last and "не" not in prev:
        return "Ты сам себе противоречишь."

    if "потом" in prev and "сейчас" in last:
        return "Так потом или сейчас?"

    if "да" in prev and "нет" in last:
        return "Переобулся за секунду."

    return None


def answer_question(text):
    if random.random() < 0.4:
        return random.choice(SHORT_ANSWERS)
    return random.choice(SHORT_ANSWERS)


@dp.message()
async def handle(message: Message):
    if message.from_user.is_bot:
        return

    text = (message.text or "").lower()
    uid = message.from_user.id

    update_context(uid, text)

    now = datetime.datetime.now().timestamp()
    last = LAST_REPLY_TIME.get(uid, 0)
    if now - last < 25 and "бот" not in text and "ты" not in text:
        return

    if "ты тут" in text or "ты жив" in text or "бот" in text:
        LAST_REPLY_TIME[uid] = now
        await message.reply("Жив. И наблюдаю 😈")
        return

    if "?" in text and random.random() < 0.7:
        LAST_REPLY_TIME[uid] = now
        await message.reply(answer_question(text))
        return

    logic = analyze_logic(uid)
    if logic and random.random() < 0.5:
        LAST_REPLY_TIME[uid] = now
        await message.reply(logic)
        return

    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id, style) VALUES (?, 'chaos')", (uid,))

        if any(w in text for w in PROMISE_WORDS):
            await db.execute("UPDATE users SET promise = promise + 1 WHERE user_id=?", (uid,))

        if len(text) > 80:
            await db.execute("UPDATE users SET talker = talker + 1 WHERE user_id=?", (uid,))

        if len(text.split()) > 15:
            await db.execute("UPDATE users SET smartass = smartass + 1 WHERE user_id=?", (uid,))

        if random.random() < 0.2:
            await db.execute("UPDATE users SET chaos = chaos + 1 WHERE user_id=?", (uid,))

        cursor = await db.execute("SELECT promise,talker,smartass,silent,chaos FROM users WHERE user_id=?", (uid,))
        data = await cursor.fetchone()

        styles = ["promise", "talker", "smartass", "silent", "chaos"]
        style = styles[data.index(max(data))]

        await db.execute("UPDATE users SET style=? WHERE user_id=?", (style, uid))
        await db.commit()

        if random.random() < 0.35:
            LAST_REPLY_TIME[uid] = now
            if random.random() < 0.7:
                await message.reply(random.choice(STYLE_PHRASES[style]))
            else:
                await message.reply(random.choice(GENERIC_PHRASES))


async def morning_task():
    while True:
        now = datetime.datetime.now()
        if now.hour == 10 and now.minute == 0:
            await bot.send_message(CHAT_ID, "Доброе утро ☀️ Делайте вид, что выспались.")
            await asyncio.sleep(60)
        await asyncio.sleep(30)


async def main():
    await init_db()
    asyncio.create_task(morning_task())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())