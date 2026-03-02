import re
import asyncio
import os
import uuid
from pathlib import Path
import yt_dlp

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile
)
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN


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


CREDIT_TEXT = (
    "━━━━━━━━━━━━━━\n"
    "📌 <b>Pinterest Downloader</b>\n"
    "💠 Credit: @iscamz\n"
    "━━━━━━━━━━━━━━"
)


# ================= START =================
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
        "✨ <b>Pinterest Downloader Bot</b> ✨\n\n"
        "📌 Send any Pinterest link\n\n"
        "🎥 Videos\n"
        "🖼 Images\n"
        "⚡ Fast • Stable • Unlimited",
        reply_markup=keyboard
    )


# ================= DOWNLOAD FUNCTION =================
async def download_with_ytdlp(url: str, output_path: str):

    ydl_opts = {
        "outtmpl": output_path,
        "format": "bv*+ba/best",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "geo_bypass": True,
        "quiet": True,
        "nocheckcertificate": True,
        "retries": 3,
    }

    loop = asyncio.get_event_loop()

    def run():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    await loop.run_in_executor(None, run)


# ================= MAIN HANDLER =================
@dp.message(F.text)
async def handle_pinterest(m: Message):

    match = PIN_REGEX.search(m.text)
    if not match:
        return

    url = match.group(1)
    status = await m.reply("🔄 Downloading...")

    file_id = uuid.uuid4().hex
    output_path = f"/tmp/{file_id}.mp4"

    try:
        await download_with_ytdlp(url, output_path)

        await status.delete()

        if not os.path.exists(output_path):
            await m.reply("❌ No downloadable media found.")
            return

        file_size = os.path.getsize(output_path)

        if file_size > 50 * 1024 * 1024:
            await m.reply("⚠️ File larger than 50MB (Telegram limit).")
            os.remove(output_path)
            return

        await m.reply_video(
            FSInputFile(output_path),
            caption="🎥 <b>HD Pinterest Download</b>\n\n" + CREDIT_TEXT
        )

        os.remove(output_path)

    except Exception as e:
        try:
            await status.edit_text(f"❌ Failed: {e}")
        except:
            await m.reply(f"❌ Error: {e}")


# ================= RUN =================
async def main():
    print("🚀 Bot Started...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
