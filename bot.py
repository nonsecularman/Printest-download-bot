import re
import asyncio
import os
import uuid
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    FSInputFile,
    InlineKeyboardMarkup,
    InlineKeyboardButton
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
        "📌 Send Pinterest Link\n\n"
        "🎥 Videos\n"
        "🖼️ Images\n"
        "📂 Albums\n\n"
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
    status = await m.reply("🔄 Downloading from Pinterest...")

    file_id = uuid.uuid4().hex
    output_template = f"/tmp/{file_id}.%(ext)s"

    try:
        # yt-dlp async run
        process = await asyncio.create_subprocess_exec(
            "yt-dlp",
            "-f", "best",
            "-o", output_template,
            url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        await process.communicate()

        # find downloaded file
        downloaded_file = None
        for file in os.listdir("/tmp"):
            if file.startswith(file_id):
                downloaded_file = f"/tmp/{file}"
                break

        try:
            await status.delete()
        except:
            pass

        if not downloaded_file:
            await m.reply("❌ Download failed.")
            return

        file_size = os.path.getsize(downloaded_file)

        if file_size > 50 * 1024 * 1024:
            await m.reply("⚠️ File larger than 50MB. Cannot upload.")
            os.remove(downloaded_file)
            return

        if downloaded_file.endswith(".mp4"):
            await m.reply_video(
                FSInputFile(downloaded_file),
                caption="🎥 <b>HD Pinterest Video</b>\n\n" + CREDIT_TEXT
            )
        else:
            await m.reply_photo(
                FSInputFile(downloaded_file),
                caption=CREDIT_TEXT
            )

        os.remove(downloaded_file)

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


# ================= RUN =================
async def main():
    print("🚀 Bot Started...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
