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
    FSInputFile
)
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import (
    BOT_TOKEN,
    CACHE_TIME,
    RATE_LIMIT,
    RATE_TIME,
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

dp = Dispatcher(storage=MemoryStorage())


# Pinterest URL Regex
PIN_REGEX = re.compile(
    r"(https?://(?:www\.)?(?:pinterest\.com/pin/\S+|pin\.it/\S+))"
)

CREDIT_TEXT = (
    "━━━━━━━━━━━━━━\n"
    "📌 <b>Pinterest Downloader</b>\n"
    "💠 Credit: @iscamz\n"
    "━━━━━━━━━━━━━━"
)


# ✅ FINAL FIXED MEDIA DOWNLOADER
async def download_media(url: str, media_type="image"):

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://www.pinterest.com/",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",

        # ✅ Brotli Fix
        "Accept-Encoding": "gzip, deflate"
    }

    try:
        timeout = aiohttp.ClientTimeout(total=60)

        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(url, allow_redirects=True) as r:

                print("DOWNLOAD STATUS:", r.status)

                if r.status != 200:
                    return None

                content = await r.read()

                # ⚠️ Pinterest Block HTML Page
                if b"<html" in content[:200].lower():
                    print("⚠️ Pinterest returned HTML instead of media")
                    return None

                # ⚠️ Small file check
                if len(content) < 5000:
                    print("⚠️ Pinterest blocked or empty file")
                    return None

                # ✅ Extension Detect
                ctype = r.headers.get("Content-Type", "")

                if "video" in ctype or media_type == "video":
                    ext = "mp4"
                elif "webp" in ctype:
                    ext = "webp"
                elif "png" in ctype:
                    ext = "png"
                else:
                    ext = "jpg"

                path = Path(f"/tmp/{uuid.uuid4().hex}.{ext}")
                path.write_bytes(content)

                return str(path)

    except Exception as e:
        print("Download Error:", e)
        return None


# 🚀 START COMMAND
@dp.message(CommandStart())
async def start_cmd(m: Message):
    await m.answer(
        "🎉 <b>Pinterest Downloader Ready!</b>\n\n"
        "📌 Send any Pinterest link:\n"
        "• <code>pin.it/xxxx</code>\n"
        "• <code>pinterest.com/pin/xxxx</code>\n\n"
        "🎥 Videos\n"
        "🖼️ Images\n"
        "📂 Albums ZIP\n\n"
        "⚡ Fast & Stable"
    )


# 🔄 MAIN PIN HANDLER
@dp.message(F.text)
async def handle_pinterest(m: Message):

    uid = m.from_user.id

    # Flood Protection
    if is_flood(uid, RATE_LIMIT, RATE_TIME):
        return await m.reply("🛑 Slow down!")

    # Daily Limit
    if uid not in OWNER_IDS and not check_daily(uid):
        return await m.reply("🚫 Daily limit reached (4/day)")

    # Extract URL
    match = PIN_REGEX.search(m.text)
    if not match:
        return

    url = match.group(1)
    status = await m.reply("🔄 Fetching Pinterest media...")

    try:
        # Cache Check
        cached = get_cache(url)

        if cached:
            images, video, error = cached
        else:
            images, video, error = await fetch_pin(url)

            if error:
                return await status.edit_text(f"❌ Error: {error}")

            set_cache(url, (images, video, None), CACHE_TIME)

        if not images and not video:
            return await status.edit_text("❌ No media found!")

        # 🎥 VIDEO DOWNLOAD
        if video:
            video_path = await download_media(video, "video")

            if video_path:
                await status.delete()
                await m.reply_video(
                    FSInputFile(video_path),
                    caption="🎥 <b>HD Pinterest Video</b>\n\n" + CREDIT_TEXT
                )
                os.remove(video_path)
            else:
                await status.delete()
                await m.reply_video(video, caption="🎥 Video Link\n\n" + CREDIT_TEXT)

            return

        # 🖼️ SINGLE IMAGE
        if len(images) == 1:

            img_path = await download_media(images[0])

            if img_path:
                await status.delete()
                await m.reply_photo(
                    FSInputFile(img_path),
                    caption=CREDIT_TEXT
                )
                os.remove(img_path)

            else:
                await status.delete()
                await m.reply_photo(
                    images[0],
                    caption="⚠️ Direct URL Mode\n\n" + CREDIT_TEXT
                )

            return

        # 📂 MULTI IMAGE ZIP
        if len(images) > 1:

            await status.edit_text("📂 Creating ZIP album...")

            zip_path = await make_zip(images, "pinterest_album")

            if zip_path:
                await status.delete()
                await m.reply_document(
                    FSInputFile(zip_path),
                    caption=f"📂 Album ({len(images)} images)\n\n{CREDIT_TEXT}"
                )
                os.remove(zip_path)

            else:
                await status.edit_text("❌ ZIP creation failed!")

            return

    except Exception as e:
        print("BOT ERROR:", e)
        await status.edit_text(f"❌ Failed: {e}")


# 🎮 INLINE MODE
@dp.inline_query()
async def inline_handler(q: InlineQuery):
    result = InlineQueryResultArticle(
        id="pinterest_dl",
        title="📌 Pinterest Downloader",
        description="Send Pinterest link to download",
        input_message_content=InputTextMessageContent(
            message_text="📌 Send Pinterest link to bot"
        )
    )
    await q.answer(results=[result], cache_time=60)


# 🧹 STARTUP CLEANUP
async def on_startup():
    cleanup_cache()
    print("🧹 Cache cleaned | Bot Ready!")


# 🚀 MAIN RUN
async def main():
    await on_startup()
    print("🚀 Bot Started...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
