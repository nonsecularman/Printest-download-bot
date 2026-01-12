import re
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineQuery, InlineQueryResultPhoto
from aiogram.filters import CommandStart

from config import BOT_TOKEN, CACHE_TIME, RATE_LIMIT, RATE_TIME
from pinterest import fetch_pin
from cache import get_cache, set_cache
from flood import is_flood
from zip_utils import make_zip

# 🔥 BOT INIT (FIXED)
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing! Check Heroku Config Vars")

bot = Bot(BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()

PIN_REGEX = re.compile(
    r"(https?://(www\.)?(pinterest\.com/pin/\S+|pin\.it/\S+))"
)

@dp.message(CommandStart())
async def start(m: Message):
    await m.answer("📌 Send Pinterest link to download images / videos")

@dp.message(F.text)
async def auto_detect(m: Message):
    match = PIN_REGEX.search(m.text)
    if not match:
        return

    if is_flood(m.from_user.id, RATE_LIMIT, RATE_TIME):
        return await m.reply("🛑 Too many requests, slow down!")

    url = match.group(1)

    cached = get_cache(url)
    if cached:
        images, video = cached
    else:
        images, video = await fetch_pin(url)
        set_cache(url, (images, video), CACHE_TIME)

    if video:
        return await m.reply_video(video, caption="🎥 HD Pinterest Video")

    if not images:
        return await m.reply("❌ No media found")

    if len(images) == 1:
        await m.reply_photo(images[0])
    else:
        zip_path = await make_zip(images, "pinterest_album")
        with open(zip_path, "rb") as f:
            await m.reply_document(
                f,
                caption="📂 Pinterest Album (ZIP)"
            )

@dp.inline_query()
async def inline_handler(q: InlineQuery):
    if not PIN_REGEX.match(q.query):
        return

    images, _ = await fetch_pin(q.query)
    results = [
        InlineQueryResultPhoto(
            id=str(i),
            photo_url=img,
            thumbnail_url=img
        )
        for i, img in enumerate(images[:5])
    ]
    await bot.answer_inline_query(q.id, results)

async def main():
    print("🔥 Bot started successfully")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
