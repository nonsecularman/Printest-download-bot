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
    CallbackQuery
)
from aiogram.filters import CommandStart, Command
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
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


# 🔥 BOT INIT with FSM
bot = Bot(
    BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# FSM States
class BotStates(StatesGroup):
    waiting_start = State()

PIN_REGEX = re.compile(
    r"(https?://(?:www\.)?(?:pinterest\.com/pin/\S+|pin\.it/\S+|pinterest\.[a-z]+/p/\S+))"
)

CREDIT_TEXT = (
    "━━━━━━━━━━━━━━\n"
    "📌 <b>Pinterest Downloader</b>\n"
    "💠 Credit: @iscamz\n"
    "━━━━━━━━━━━━━━"
)

# 📥 HIGH-QUALITY MEDIA DOWNLOADER (unchanged)
async def download_media(url: str, media_type: str = "image") -> str | None:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.pinterest.com/",
        "Accept": "image/webp,image/apng,image/*,*/*;q=0.8"
    }
    
    ext = "mp4" if media_type == "video" else "jpg"
    path = Path(f"/tmp/{uuid.uuid4().hex}.{ext}")
    
    try:
        timeout = aiohttp.ClientTimeout(total=45)
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(url, allow_redirects=True) as r:
                if r.status != 200:
                    return None
                
                content = await r.read()
                if len(content) < 1024:
                    return None
                
                path.write_bytes(content)
                return str(path)
    except Exception:
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

# 🆕 PRIVATE START - No force-sub initially
@dp.message(CommandStart())
async def private_start(m: Message, state: FSMContext):
    uid = m.from_user.id
    
    # 👑 Owners bypass everything
    if uid in OWNER_IDS:
        await state.clear()
        return await show_main_menu(m)
    
    # Check if already subscribed
    if await force_sub(m):
        await state.clear()
        return await show_main_menu(m)
    
    # 🚀 PRIVATE START MODE
    keyboard = [
        [{"text": "✅ Join Channels", "callback_data": "join_channels"}],
        [{"text": "ℹ️ How to use", "callback_data": "how_to_use"}]
    ]
    
    await state.set_state(BotStates.waiting_start)
    await m.answer(
        "🎉 <b>Welcome to Pinterest Downloader!</b>\n\n"
        "📌 Send any Pinterest link to start downloading\n\n"
        "⚠️ <b>One-time setup:</b> Join 2 channels to unlock unlimited access\n\n"
        "👇 <b>Choose option below:</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

# 📱 MAIN MENU
async def show_main_menu(m: Message):
    await m.answer(
        "📌 <b>Pinterest Downloader Ready!</b>\n\n"
        "🔗 Just send Pinterest link:\n"
        "• <code>pin.it/ABC123</code>\n"
        "• <code>pinterest.com/pin/123456</code>\n\n"
        "🎥 HD Videos\n"
        "🖼️ HQ Images\n"
        "📂 Multi-image ZIPs\n\n"
        "⚠️ <b>Daily limit: 4 downloads</b>\n"
        "👑 <b>Owner: Unlimited</b>",
        parse_mode="HTML"
    )

# 🔘 CALLBACK HANDLERS
@dp.callback_query(F.data == "join_channels")
async def join_channels_cb(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🔗 <b>Join both channels:</b>\n\n"
        f"👉 <a href='{FORCE_CHANNEL_1}'>Channel 1</a>\n"
        f"👉 <a href='{FORCE_CHANNEL_2}'>Channel 2</a>\n\n"
        "✅ Join karke <b>Check Subscription</b> dabao",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [{"text": "✅ Check Subscription", "callback_data": "check_sub"}],
            [{"text": "🔙 Back", "callback_data": "back_start"}]
        ])
    )

@dp.callback_query(F.data == "check_sub")
async def check_sub_cb(callback: CallbackQuery, state: FSMContext):
    if await force_sub(callback.message):
        await state.clear()
        await callback.message.edit_text(
            "✅ <b>Subscription verified!</b>\n\nBot ready to use 🚀",
            reply_markup=None
        )
        await show_main_menu(callback.message)
    else:
        await callback.answer("❌ Still not joined both channels!", show_alert=True)

@dp.callback_query(F.data == "how_to_use")
async def how_to_use_cb(callback: CallbackQuery):
    await callback.message.edit_text(
        "📖 <b>How to use:</b>\n\n"
        "1️⃣ Send Pinterest link\n"
        "2️⃣ Get HD downloads instantly\n\n"
        "✅ <b>Supports:</b>\n"
        "• Videos (MP4)\n"
        "• Single images (JPG)\n"
        "• Multi-images (ZIP)\n\n"
        "⚡ <b>Fast & High Quality</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [{"text": "🔙 Back", "callback_data": "back_start"}]
        ])
    )

@dp.callback_query(F.data == "back_start")
async def back_start_cb(callback: CallbackQuery, state: FSMContext):
    await private_start(callback.message, state)
    await callback.message.delete()

# 🔄 TEXT HANDLER - Works after subscription OR private mode
@dp.message(F.text, BotStates.waiting_start)
async def handle_pinterest_private(m: Message, state: FSMContext):
    uid = m.from_user.id
    
    # Quick sub check for private users
    if uid not in OWNER_IDS and not await force_sub(m):
        await m.reply(
            "⚠️ <b>Please join channels first!</b>\n\n"
            f"👉 <a href='{FORCE_CHANNEL_1}'>Channel 1</a>\n"
            f"👉 <a href='{FORCE_CHANNEL_2}'>Channel 2</a>"
        )
        return
    
    await state.clear()
    await handle_pinterest_main(m)

@dp.message(F.text)
async def handle_pinterest_main(m: Message):
    # 🔥 FLOOD + DAILY LIMIT
    uid = m.from_user.id
    if is_flood(uid, RATE_LIMIT, RATE_TIME):
        return await m.reply("🛑 <b>Slow down!</b>")

    if uid not in OWNER_IDS and not check_daily(uid):
        return await m.reply(
            "🚫 <b>Daily limit reached!</b>\n\n"
            "📊 Only <b>4 downloads</b> per day\n"
            "⏰ Try again tomorrow"
        )

    # 🔍 EXTRACT PIN URL
    match = PIN_REGEX.search(m.text)
    if not match:
        return

    url = match.group(1)
    status_msg = await m.reply("🔄 <b>Fetching high-quality media...</b>")

    try:
        # 💾 CACHE CHECK
        cached = get_cache(url)
        if cached:
            images, video, error = cached
        else:
            images, video, error = await fetch_pin(url)
            if error:
                await status_msg.edit_text(f"❌ <b>Error:</b> {error}")
                return
            
            set_cache(url, (images, video, None), CACHE_TIME)

        if not images and not video:
            await status_msg.edit_text("❌ <b>No media found</b> in this pin")
            return

        # 🎥 VIDEO FIRST
        if video:
            video_path = await download_media(video, "video")
            if video_path and os.path.exists(video_path):
                try:
                    doc = FSInputFile(video_path)
                    await status_msg.delete()
                    await m.reply_video(
                        doc,
                        caption=f"🎥 <b>HD Pinterest Video</b>\n\n{CREDIT_TEXT}",
                        supports_streaming=True
                    )
                except TelegramBadRequest:
                    await m.reply_video(video, caption=f"🎥 <b>HD Video</b>\n\n{CREDIT_TEXT}")
                finally:
                    os.remove(video_path)
            else:
                await status_msg.delete()
                await m.reply_video(video, caption=f"🎥 <b>HD Video</b>\n\n{CREDIT_TEXT}")
            return

        # 🖼️ SINGLE IMAGE
        if images and len(images) == 1:
            img_path = await download_media(images[0])
            if img_path and os.path.exists(img_path):
                try:
                    photo = FSInputFile(img_path)
                    await status_msg.delete()
                    await m.reply_photo(photo, caption=CREDIT_TEXT)
                finally:
                    os.remove(img_path)
            else:
                await status_msg.delete()
                await m.reply_photo(images[0], caption=CREDIT_TEXT)
            return

        # 📂 MULTIPLE IMAGES → ZIP
        if len(images) > 1:
            await status_msg.edit_text("📂 <b>Creating ZIP album...</b>")
            zip_path = await make_zip(images, "pinterest_album")
            if zip_path and os.path.exists(zip_path):
                try:
                    doc = FSInputFile(zip_path)
                    await status_msg.delete()
                    await m.reply_document(
                        doc,
                        caption=f"📂 <b>Pinterest Album</b> ({len(images)} images)\n\n{CREDIT_TEXT}"
                    )
                finally:
                    os.remove(zip_path)
            else:
                await status_msg.edit_text("❌ <b>ZIP creation failed</b>")

    except Exception as e:
        await status_msg.edit_text("❌ <b>Download failed</b>")

# 🎮 INLINE MODE
@dp.inline_query()
async def inline_handler(q: InlineQuery):
    result = InlineQueryResultArticle(
        id="pinterest_dl",
        title="📌 Pinterest Downloader",
        description="Send link to bot for HD downloads",
        input_message_content=InputTextMessageContent(
            message_text="📌 Send Pinterest link to @yourbotusername"
        )
    )
    await q.answer(results=[result], cache_time=60)

# 🧹 CLEANUP
async def on_startup():
    cleanup_cache()
    print("🧹 Cache cleaned | Bot ready!")

async def main():
    print("🚀 Starting Pinterest Downloader Bot...")
    await on_startup()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
