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
    InputMediaPhoto
)
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, CACHE_TIME
from pinterest import fetch_pin
from cache import get_cache, set_cache, cleanup_cache


# ================== BOT INIT ==================
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)

dp = Dispatcher(storage=MemoryStorage())


# ================== REGEX ==================
PIN_REGEX = re.compile(
    r"(https?://(?:www\.)?(?:pinterest\.com/pin/\S+|pin\.it/\S+))"
)


# ================== CREDIT ==================
CREDIT_TEXT = (
    "━━━━━━━━━━━━━━\n"
    "📌 <b>Pinterest Downloader</b>\n"
    "💠 Credit: @iscamz\n"
    "━━━━━━━━━━━━━━"
)


# ================== MEDIA DOWNLOADER ==================
async def download_media(url: str, media_type: str = "image"):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.pinterest.com/",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate"
    }

    try:
        timeout = aiohttp.ClientTimeout(total=60)

        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(url, allow_redirects=True) as r:

                if r.status != 200:
                    return None

                content = await r.read()

                if b"<html" in content[:200].lower():
                    return None

                if len(content) < 5000:
                    return None

                ctype = r.headers.get("content-type", "")

                if "video" in ctype or media_type == "video":
                    ext = "mp4"
                elif "png" in ctype:
                    ext = "png"
                elif "webp" in ctype:
                    ext = "webp"
                else:
                    ext = "jpg"

                path = Path(f"/tmp/{uuid.uuid4().hex}.{ext}")
                path.write_bytes(content)

                return str(path)

    except Exception:
        return None


# ================== START ==================
@dp.message(CommandStart())
async def start_cmd(m: Message):
    await m.answer(
        "🎉 <b>Pinterest Downloader Ready!</b>\n\n"
        "📌 Send any Pinterest link:\n"
        "• <code>pin.it/xxxx</code>\n"
        "• <code>pinterest.com/pin/xxxx</code>\n\n"
        "🎥 Videos\n"
        "🖼️ Images\n"
        "🖼️ Multi Images → Album\n\n"
        "⚡ Unlimited & Fast"
    )


# ================== MAIN HANDLER ==================
@dp.message(F.text)
async def handle_pinterest(m: Message):

    match = PIN_REGEX.search(m.text)
    if not match:
        return

    url = match.group(1)
    status = await m.reply("🔄 Fetching Pinterest media...")

    try:
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

        # ---------- VIDEO ----------
        if video:
            video_path = await download_media(video, "video")
            await status.delete()

            if video_path:
                await m.reply_video(
                    FSInputFile(video_path),
                    caption="🎥 <b>HD Pinterest Video</b>\n\n" + CREDIT_TEXT
                )
                os.remove(video_path)
            else:
                await m.reply_video(video, caption="🎥 Video Link\n\n" + CREDIT_TEXT)

            return

        # ---------- SINGLE IMAGE ----------
        if len(images) == 1:
            img_path = await download_media(images[0])
            await status.delete()

            if img_path:
                await m.reply_photo(FSInputFile(img_path), caption=CREDIT_TEXT)
                os.remove(img_path)
            else:
                await m.reply_photo(images[0], caption=CREDIT_TEXT)

            return

        # ---------- MULTIPLE IMAGES ----------
        if len(images) > 1:
            await status.edit_text("🖼️ Sending images as Album...")

            media_group = [
                InputMediaPhoto(media=img)
                for img in images[:10]
            ]

            await status.delete()
            await m.reply_media_group(media_group)
            await m.reply(CREDIT_TEXT)

            if len(images) > 10:
                await m.reply("⚠️ Only first 10 images sent (Telegram limit)")

    except Exception as e:
        await status.edit_text(f"❌ Failed: {e}")


# ================== INLINE MODE (FIXED) ==================
@dp.inline_query()
async def inline_handler(q: InlineQuery):
    result = InlineQueryResultArticle(
        id="pinterest_dl",
        title="📌 Pinterest Downloader",
        description="Send Pinterest link to download",
        input_message_content=InputTextMessageContent(
            message_text="📌 Send Pinterest link to the bot"
        )
    )
    await q.answer(results=[result], cache_time=60)


# ================== STARTUP ==================
async def on_startup():
    cleanup_cache()
    print("🧹 Cache cleaned | Bot Ready!")


# ================== RUN ==================
async def main():
    await on_startup()
    print("🚀 Bot Started...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
