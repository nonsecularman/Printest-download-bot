import re
import asyncio
import os
import uuid
import aiohttp
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    FSInputFile,
    CallbackQuery,
    InlineKeyboardMarkup
)
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

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
from cache import get_cache, set_cache, cleanup_cache
from flood import is_flood, check_daily
from zip_utils import make_zip


# 🔥 BOT INIT
bot = Bot(
    BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


# FSM States
class BotStates(StatesGroup):
    waiting_start = State()


# Pinterest URL Regex
PIN_REGEX = re.compile(
    r"(https?://(?:www\.)?(?:pinterest\.com/pin/\S+|pin\.it/\S+|pinterest\.[a-z]+/p/\S+))"
)

CREDIT_TEXT = (
    "━━━━━━━━━━━━━━\n"
    "📌 <b>Pinterest Downloader</b>\n"
    "💠 Credit: @iscamz\n"
    "━━━━━━━━━━━━━━"
)

# ✅ FIXED MEDIA DOWNLOADER
async def download_media(url: str, media_type="image"):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.pinterest.com/",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9"
    }

    try:
        timeout = aiohttp.ClientTimeout(total=60)

        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(url, allow_redirects=True) as r:

                print("DOWNLOAD STATUS:", r.status)

                if r.status != 200:
                    return None

                content = await r.read()

                if len(content) < 5000:
                    print("⚠️ Pinterest Blocked File")
                    return None

                # Detect extension
                ctype = r.headers.get("Content-Type", "")
                if "webp" in ctype:
                    ext = "webp"
                elif "png" in ctype:
                    ext = "png"
                elif media_type == "video":
                    ext = "mp4"
                else:
                    ext = "jpg"

                path = Path(f"/tmp/{uuid.uuid4().hex}.{ext}")
                path.write_bytes(content)

                return str(path)

    except Exception as e:
        print("Download Error:", e)
        return None


# 🔒 FORCE SUBSCRIBE
async def force_sub(m: Message) -> bool:
    uid = m.from_user.id
    try:
        ch1 = await bot.get_chat_member(FORCE_CHANNEL_1, uid)
        ch2 = await bot.get_chat_member(FORCE_CHANNEL_2, uid)
        return (ch1.status in ("member", "administrator", "creator") and
                ch2.status in ("member", "administrator", "creator"))
    except:
        return False


# 🚀 START COMMAND
@dp.message(CommandStart())
async def private_start(m: Message, state: FSMContext):

    uid = m.from_user.id

    if uid in OWNER_IDS:
        await state.clear()
        return await show_main_menu(m)

    if await force_sub(m):
        await state.clear()
        return await show_main_menu(m)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [{"text": "✅ Join Channels", "callback_data": "join_channels"}],
        [{"text": "ℹ️ How to use", "callback_data": "how_to_use"}]
    ])

    await state.set_state(BotStates.waiting_start)

    await m.answer(
        "🎉 <b>Welcome to Pinterest Downloader!</b>\n\n"
        "📌 Send any Pinterest link to start downloading\n\n"
        "⚠️ Join both channels first to unlock bot\n\n"
        "👇 Choose option below:",
        reply_markup=keyboard
    )


# 📌 MAIN MENU
async def show_main_menu(m: Message):
    await m.answer(
        "📌 <b>Pinterest Downloader Ready!</b>\n\n"
        "🔗 Send Pinterest link:\n"
        "• <code>pin.it/xxxx</code>\n"
        "• <code>pinterest.com/pin/xxxx</code>\n\n"
        "🎥 Videos\n"
        "🖼️ Images\n"
        "📂 Albums ZIP\n\n"
        "⚠️ Daily limit: 4 downloads\n"
        "👑 Owner: Unlimited"
    )


# 🔄 PIN HANDLER
@dp.message(F.text)
async def handle_pinterest_main(m: Message):

    uid = m.from_user.id

    if is_flood(uid, RATE_LIMIT, RATE_TIME):
        return await m.reply("🛑 Slow down!")

    if uid not in OWNER_IDS and not check_daily(uid):
        return await m.reply("🚫 Daily limit reached (4/day)")

    match = PIN_REGEX.search(m.text)
    if not match:
        return

    url = match.group(1)
    status_msg = await m.reply("🔄 Fetching Pinterest media...")

    try:
        cached = get_cache(url)

        if cached:
            images, video, error = cached
        else:
            images, video, error = await fetch_pin(url)

            if error:
                return await status_msg.edit_text(f"❌ Error: {error}")

            set_cache(url, (images, video, None), CACHE_TIME)

        if not images and not video:
            return await status_msg.edit_text("❌ No media found")

        # 🎥 VIDEO
        if video:
            video_path = await download_media(video, "video")

            if video_path:
                await status_msg.delete()
                await m.reply_video(FSInputFile(video_path),
                                   caption="🎥 HD Pinterest Video\n\n" + CREDIT_TEXT)
                os.remove(video_path)
            else:
                await status_msg.delete()
                await m.reply_video(video, caption="🎥 HD Video\n\n" + CREDIT_TEXT)
            return

        # 🖼️ SINGLE IMAGE
        if len(images) == 1:

            img_path = await download_media(images[0])

            if img_path:
                await status_msg.delete()
                await m.reply_photo(FSInputFile(img_path),
                                    caption=CREDIT_TEXT)
                os.remove(img_path)
            else:
                await status_msg.delete()
                await m.reply_photo(images[0], caption=CREDIT_TEXT)

            return

        # 📂 MULTI IMAGE ZIP
        if len(images) > 1:
            await status_msg.edit_text("📂 Creating ZIP album...")

            zip_path = await make_zip(images, "pinterest_album")

            if zip_path:
                await status_msg.delete()
                await m.reply_document(FSInputFile(zip_path),
                                       caption=f"📂 Album ({len(images)} images)\n\n{CREDIT_TEXT}")
                os.remove(zip_path)
            else:
                await status_msg.edit_text("❌ ZIP failed")

    except Exception as e:
        print("BOT ERROR:", e)
        await status_msg.edit_text(f"❌ Failed: {e}")


# 🎮 INLINE MODE
@dp.inline_query()
async def inline_handler(q: InlineQuery):
    result = InlineQueryResultArticle(
        id="pinterest_dl",
        title="📌 Pinterest Downloader",
        description="Send Pinterest link to bot",
        input_message_content=InputTextMessageContent(
            message_text="📌 Send Pinterest link to bot"
        )
    )
    await q.answer(results=[result], cache_time=60)


# 🧹 CLEANUP
async def on_startup():
    cleanup_cache()
    print("🧹 Cache cleaned | Bot Ready!")


# 🚀 MAIN
async def main():
    await on_startup()
    print("🚀 Bot Started...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
