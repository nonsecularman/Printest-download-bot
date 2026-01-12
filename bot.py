import re
import asyncio

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    InlineQuery,
    InlineQueryResultPhoto
)
from aiogram.filters import CommandStart
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

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


# 🔥 BOT INIT
bot = Bot(BOT_TOKEN, parse_mode="HTML")
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


# 🔒 FORCE SUBSCRIBE
async def force_sub(m: Message) -> bool:
    uid = m.from_user.id
    try:
        ch1 = await bot.get_chat_member(FORCE_CHANNEL_1, uid)
        ch2 = await bot.get_chat_member(FORCE_CHANNEL_2, uid)

        if ch1.status in ("member", "administrator", "creator") and \
           ch2.status in ("member", "administrator", "creator"):
            return True

        raise TelegramBadRequest("User not joined")

    except (TelegramBadRequest, TelegramForbiddenError):
        await m.answer(
            "🚫 <b>Before using me, join both channels</b>\n\n"
            f"👉 {FORCE_CHANNEL_1}\n"
            f"👉 {FORCE_CHANNEL_2}\n\n"
            "✅ Joined? Send /start again"
        )
        return False


# 🧠 START — PSYCHOLOGIST MODE
@dp.message(CommandStart())
async def start(m: Message):
    if not await force_sub(m):
        return

    await m.answer(
        "👋 ʜᴇʏ… ʙʀᴇᴀᴛʜᴇ.\n\n"
        "ɪ ᴅᴏɴ’ᴛ ᴊᴜᴅɢᴇ.\n"
        "ɪ ᴊᴜsᴛ ᴏʙsᴇʀᴠᴇ ʏᴏᴜʀ ᴘɪɴᴛᴇʀᴇsᴛ ᴛᴀsᴛᴇ 👀\n\n"
        "🎥 ɴᴏᴡ ᴀᴄᴛɪᴠᴇ: ᴘғᴘ ᴍᴏᴅᴇ\n"
        "🧪 ᴏᴛʜᴇʀ ᴍᴏᴅᴇs: ᴄᴏᴍɪɴɢ sᴏᴏɴ… ʜᴇᴀʟɪɴɢ ɪɴ ᴘʀᴏɢʀᴇss 💭\n\n"
        "📌 ᴅʀᴏᴘ ᴀ ᴘɪɴᴛᴇʀᴇsᴛ ʟɪɴᴋ\n"
        "ɪ’ʟʟ ᴛᴀᴋᴇ ᴄᴀʀᴇ ᴏғ ᴛʜᴇ ʀᴇsᴛ 🫶\n\n"
        "⚠️ ᴅᴀɪʟʏ ʟɪᴍɪᴛ: 4 ᴅᴏᴡɴʟᴏᴀᴅs\n"
        "👑 ᴏᴡɴᴇʀs: ᴜɴʟɪᴍɪᴛᴇᴅ"
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
        return await m.reply("🛑 Slow down. You’re safe here.")

    # 📌 Daily limit
    if m.from_user.id not in OWNER_IDS:
        if not check_daily(m.from_user.id):
            return await m.reply(
                "🧠 <b>Daily limit reached.</b>\n"
                "Rest. Come back tomorrow 🌙"
            )

    url = match.group(1)

    cached = get_cache(url)
    if cached:
        images, video = cached
    else:
        images, video = await fetch_pin(url)
        set_cache(url, (images, video), CACHE_TIME)

    # 🎥 VIDEO
    if video:
        return await m.reply_video(
            video,
            caption=f"🎥 HD Pinterest Video\n\n{CREDIT_TEXT}"
        )

    if not images:
        return await m.reply("❌ No media found. Maybe wrong link?")

    # 🖼 SINGLE IMAGE
    if len(images) == 1:
        return await m.reply_photo(
            images[0],
            caption=CREDIT_TEXT
        )

    # 📂 MULTIPLE → ZIP
    zip_path = await make_zip(images, "pinterest_album")
    with open(zip_path, "rb") as f:
        await m.reply_document(
            f,
            caption=f"📂 Pinterest Album (ZIP)\n\n{CREDIT_TEXT}"
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
    print("🧠 Psychologist Bot is listening…")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
