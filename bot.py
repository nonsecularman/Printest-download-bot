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
    InputMediaPhoto,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, CACHE_TIME
from pinterest import fetch_pin
from cache import get_cache, set_cache, cleanup_cache


# ================= BOT INIT =================
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)

dp = Dispatcher(storage=MemoryStorage())


# ================= REGEX =================
PIN_REGEX = re.compile(
    r"(https?://(?:www\.)?(?:pinterest\.com/pin/\S+|pin\.it/\S+))"
)


# ================= CREDIT =================
CREDIT_TEXT = (
    "━━━━━━━━━━━━━━\n"
    "📌 <b>Pinterest Downloader</b>\n"
    "💠 Credit: @iscamz\n"
    "━━━━━━━━━━━━━━"
)


# ================= SAFE MEDIA DOWNLOADER =================
async def download_media(url: str, media_type: str = "image"):

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.pinterest.com/"
    }

    try:
        timeout = aiohttp.ClientTimeout(total=120)

        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(url, allow_redirects=True) as r:

                if r.status != 200:
                    return None

                content_type = r.headers.get("content-type", "")

                if media_type == "video" and "video" not in content_type:
                    return None

                file_size = int(r.headers.get("content-length", 0))

                if file_size > 50 * 1024 * 1024:
                    return "TOO_LARGE"

                ext = "mp4" if media_type == "video" else "jpg"
                path = Path(f"/tmp/{uuid.uuid4().hex}.{ext}")

                with open(path, "wb") as f:
                    async for chunk in r.content.iter_chunked(1024 * 1024):
                        f.write(chunk)

                return str(path)

    except Exception:
        return None


# ================= PREMIUM START =================
@dp.message(CommandStart())
async def start_cmd(m: Message):

    bot_info = await bot.me()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📢 Updates Channel",
                    url="https://t.me/iscamz"
                )
            ],
            [
                InlineKeyboardButton(
                    text="➕ Add To Group",
                    url=f"https://t.me/{bot_info.username}?startgroup=true"
                )
            ]
        ]
    )

    await m.answer(
        "╭━━━━━━━━━━━━━━━━━━╮\n"
        "✨ <b>Pinterest Downloader Bot</b> ✨\n"
        "╰━━━━━━━━━━━━━━━━━━╯\n\n"
        "📌 <b>Send Pinterest Link</b>\n\n"
        "🎥 Videos\n"
        "🖼️ Images\n"
        "📂 Multi Images → Album\n\n"
        "⚡ Fast • Stable • Unlimited",
        reply_markup=keyboard
    )


# ================= MAIN HANDLER =================
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
                await status.edit_text(f"❌ Error: {error}")
                return

            set_cache(url, (images, video, None), CACHE_TIME)

        if not images and not video:
            await status.edit_text("❌ No media found!")
            return

        # ================= VIDEO =================
        if video:
            await status.edit_text("🎥 Downloading video...")

            video_path = await download_media(video, "video")

            try:
                await status.delete()
            except:
                pass

            if video_path == "TOO_LARGE":
                await m.reply(
                    "⚠️ Video larger than 50MB.\n\nDirect link:\n" + video
                )
                return

            if video_path:
                await m.reply_video(
                    FSInputFile(video_path),
                    caption="🎥 <b>HD Pinterest Video</b>\n\n" + CREDIT_TEXT
                )
                os.remove(video_path)
            else:
                await m.reply("⚠️ Video download failed.\n\n" + video)

            return

        # ================= SINGLE IMAGE =================
        if len(images) == 1:
            img_path = await download_media(images[0])

            try:
                await status.delete()
            except:
                pass

            if img_path:
                await m.reply_photo(FSInputFile(img_path), caption=CREDIT_TEXT)
                os.remove(img_path)
            else:
                await m.reply_photo(images[0], caption=CREDIT_TEXT)

            return

        # ================= MULTIPLE IMAGES =================
        if len(images) > 1:
            await status.edit_text("🖼️ Downloading images...")

            media_group = []
            files = []

            for img in images[:10]:
                img_path = await download_media(img)

                if img_path:
                    media_group.append(
                        InputMediaPhoto(
                            media=FSInputFile(img_path)
                        )
                    )
                    files.append(img_path)

                await asyncio.sleep(0.2)

            if not media_group:
                await status.edit_text("❌ Failed to download images!")
                return

            try:
                await status.delete()
            except:
                pass

            await m.reply_media_group(media_group)
            await m.reply(CREDIT_TEXT)

            for f in files:
                try:
                    os.remove(f)
                except:
                    pass

            return

    except Exception as e:
        try:
            await status.edit_text(f"❌ Failed: {e}")
        except:
            await m.reply(f"❌ Error: {e}")


# ================= INLINE =================
@dp.inline_query()
async def inline_handler(q: InlineQuery):
    result = InlineQueryResultArticle(
        id="pinterest_dl",
        title="📌 Pinterest Downloader",
        description="Send Pinterest link",
        input_message_content=InputTextMessageContent(
            message_text="📌 Send Pinterest link to bot"
        )
    )
    await q.answer(results=[result], cache_time=60)


# ================= STARTUP =================
async def on_startup():
    cleanup_cache()
    print("🧹 Cache cleaned | Bot Ready!")


# ================= RUN =================
async def main():
    await on_startup()
    print("🚀 Bot Started...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
