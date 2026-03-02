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
        "Accept": "*/*"
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

                if len(content) < 4000:
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


# ================== PREMIUM START ==================
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
        "📌 <b>Send Any Pinterest Link</b>\n\n"
        "🔹 <code>pin.it/xxxx</code>\n"
        "🔹 <code>pinterest.com/pin/xxxx</code>\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🎥 <b>Download Videos</b>\n"
        "🖼️ <b>Single Images</b>\n"
        "📂 <b>Multi Images → Album</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "⚡ <b>Fast • Stable • Unlimited</b>\n\n"
        "💡 Just paste link and enjoy!",
        reply_markup=keyboard
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
                await status.edit_text(f"❌ Error: {error}")
                return

            set_cache(url, (images, video, None), CACHE_TIME)

        if not images and not video:
            await status.edit_text("❌ No media found!")
            return

        # ========= VIDEO =========
        if video:
            video_path = await download_media(video, "video")

            try:
                await status.delete()
            except:
                pass

            if video_path:
                await m.reply_video(
                    FSInputFile(video_path),
                    caption="🎥 <b>HD Pinterest Video</b>\n\n" + CREDIT_TEXT
                )
                os.remove(video_path)
            else:
                await m.reply_video(video, caption="🎥 Video Link\n\n" + CREDIT_TEXT)

            return

        # ========= SINGLE IMAGE =========
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

        # ========= MULTIPLE IMAGES =========
        if len(images) > 1:
            await status.edit_text("🖼️ Downloading images...")

            media_group = []
            downloaded_files = []

            for img in images[:10]:
                img_path = await download_media(img)

                if img_path:
                    media_group.append(
                        InputMediaPhoto(media=FSInputFile(img_path))
                    )
                    downloaded_files.append(img_path)

                await asyncio.sleep(0.3)

            if not media_group:
                await status.edit_text("❌ Failed to download images!")
                return

            try:
                await status.delete()
            except:
                pass

            await m.reply_media_group(media_group)
            await m.reply(CREDIT_TEXT)

            for file in downloaded_files:
                try:
                    os.remove(file)
                except:
                    pass

            if len(images) > 10:
                await m.reply("⚠️ Only first 10 images sent (Telegram limit)")

            return

    except Exception as e:
        try:
            await status.edit_text(f"❌ Failed: {e}")
        except:
            await m.reply(f"❌ Error: {e}")


# ================== INLINE MODE ==================
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
