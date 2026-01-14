import re
import asyncio
import os
import uuid
import aiohttp

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent
)
from aiogram.filters import CommandStart
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.client.default import DefaultBotProperties

from config import (
    BOT_TOKEN,
    CACHE_TIME,
    RATE_LIMIT,
    RATE_TIME,
    FORCE_CHANNEL_1,
    FORCE_CHANNEL_2,
    OWNER_IDS
)

from pinterest import fetch_pin
from cache import get_cache, set_cache
from flood import is_flood, check_daily
from zip_utils import make_zip


# 🔥 BOT INIT (aiogram v3)
bot = Bot(
    BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher()

PIN_REGEX = re.compile(
    r"(https?://(www\.)?(pinterest\.com/pin/\S+|pin\.it/\S+))"
)

CREDIT_TEXT = (
    "━━━━━━━━━━━━━━\n"
    "📌 Pinterest Download\n"
    "💠 Credit: @iscamz\n"
    "━━━━━━━━━━━━━━"
)


# 📥 IMAGE DOWNLOADER (Pinterest fix)
async def download_image(url: str) -> str | None:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as r:
                if r.status != 200:
                    return None

                path = f"/tmp/{uuid.uuid4().hex}.jpg"
                with open(path, "wb") as f:
                    f.write(await r.read())
                return path
    except:
        return None


# 🔒 FORCE SUBSCRIBE
async def force_sub(m: Message) -> bool:
    uid = m.from_user.id
    try:
        ch1 = await bot.get_chat_member(FORCE_CHANNEL_1, uid)
        ch2 = await bot.get_chat_member(FORCE_CHANNEL_2, uid)

        if ch1.status in ("member", "administrator", "creator") and \
           ch2.status in ("member", "administrator", "creator"):
            return True

        raise TelegramBadRequest("Not joined")

    except (TelegramBadRequest, TelegramForbiddenError):
        await m.answer(
            "🚫 <b>Bot use karne se pehle dono channel join karo</b>\n\n"
            f"👉 {FORCE_CHANNEL_1}\n"
            f"👉 {FORCE_CHANNEL_2}\n\n"
            "✅ Join ke baad /start bhejo"
        )
        return False


@dp.message(CommandStart())
async def start(m: Message):
    if not await force_sub(m):
        return

    await m.answer(
        "📌 <b>Pinterest Downloader Bot</b>\n\n"
        "🔹 Pinterest link bhejo\n"
        "🔹 Images / Videos download honge\n\n"
        "⚠️ Daily limit: <b>4 downloads</b>\n"
        "👑 Owner: Unlimited"
    )


@dp.message(F.text)
async def auto_detect(m: Message):
    if not await force_sub(m):
        return

    match = PIN_REGEX.search(m.text)
    if not match:
        return

    # 🚫 Flood control
    if is_flood(m.from_user.id, RATE_LIMIT, RATE_TIME):
        return await m.reply("🛑 Thoda slow karo")

    # 📌 Daily limit
    if m.from_user.id not in OWNER_IDS:
        if not check_daily(m.from_user.id):
            return await m.reply(
                "🚫 <b>Daily limit khatam</b>\n\n"
                "📌 Sirf 4 Pinterest downloads / day allowed"
            )

    url = match.group(1)

    cached = get_cache(url)
    if cached:
        images, video = cached
    else:
        data = await fetch_pin(url)     # 🔥 SAFE UNPACK
        images = data[0]
        video = data[1]
        set_cache(url, (images, video), CACHE_TIME)

    # 🎥 VIDEO
    if video:
        return await m.reply_video(
            video,
            caption=f"🎥 HD Pinterest Video\n\n{CREDIT_TEXT}"
        )

    if not images:
        return await m.reply("❌ No media found")

    # 🖼 SINGLE IMAGE
    if len(images) == 1:
        img_path = await download_image(images[0])
        if not img_path:
            return await m.reply("❌ Image download failed")

        with open(img_path, "rb") as f:
            await m.reply_photo(f, caption=CREDIT_TEXT)

        os.remove(img_path)
        return

    # 📂 MULTIPLE IMAGES → ZIP
    zip_path = await make_zip(images, "pinterest_album")
    with open(zip_path, "rb") as f:
        await m.reply_document(
            f,
            caption=f"📂 Pinterest Album (ZIP)\n\n{CREDIT_TEXT}"
        )


# 🔎 INLINE MODE (SAFE)
@dp.inline_query()
async def inline_handler(q: InlineQuery):
    result = InlineQueryResultArticle(
        id="pinterest",
        title="📌 Pinterest Downloader",
        description="Bot ke private chat me Pinterest link bhejo",
        input_message_content=InputTextMessageContent(
            message_text="📌 Bot ke private chat me Pinterest link bhejo"
        )
    )

    await bot.answer_inline_query(
        q.id,
        results=[result],
        cache_time=5
    )


async def main():
    print("🔥 Bot started successfully")
    await dp.start_polling(bot)


# ✅ ENTRY POINT (FINAL)
if __name__ == "__main__":
    asyncio.run(main())
