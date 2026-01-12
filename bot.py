import re
import asyncio
import os
import uuid
import aiohttp

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import CommandStart

from config import BOT_TOKEN
from pinterest import fetch_pin

bot = Bot(BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()

PIN_REGEX = re.compile(
    r"(https?://(www\.)?(pinterest\.com/pin/\S+|pin\.it/\S+))"
)

CREDIT_TEXT = "📌 Pinterest Downloader\n💠 @iscamz"


# 🔥 VIDEO DOWNLOADER (MOST IMPORTANT)
async def download_video(url: str) -> str:
    path = f"/tmp/{uuid.uuid4()}.mp4"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise Exception("Video download failed")

            with open(path, "wb") as f:
                while True:
                    chunk = await resp.content.read(1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)

    return path


@dp.message(CommandStart())
async def start(m: Message):
    await m.answer("📌 Pinterest link bhejo (video + image supported)")


@dp.message(F.text)
async def handle_pin(m: Message):
    match = PIN_REGEX.search(m.text)
    if not match:
        return

    url = match.group(1)

    await m.reply("⏳ Downloading...")

    images, video = await fetch_pin(url)

    # 🎥 VIDEO FIX (DOWNLOAD → UPLOAD)
    if video:
        try:
            video_path = await download_video(video)

            with open(video_path, "rb") as f:
                await m.reply_video(
                    f,
                    caption=f"🎥 Pinterest Video\n\n{CREDIT_TEXT}"
                )

            os.remove(video_path)
            return

        except Exception as e:
            return await m.reply("❌ Video download failed")

    # 🖼 IMAGE FALLBACK
    if images:
        await m.reply_photo(images[0], caption=CREDIT_TEXT)
    else:
        await m.reply("❌ No media found")


async def main():
    print("🔥 Bot started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
