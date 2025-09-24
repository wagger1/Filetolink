import time
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
from info import URL, BOT_USERNAME, BIN_CHANNEL, MAX_FILES, FSUB, CHANNEL
from database.users_db import db
from web.utils.file_properties import get_hash
from utils import get_size
from plugins.avbot import av_verification, is_user_allowed, is_user_joined
from Script import script

def valid_url(url: str) -> str:
    """Ensure URL is safe for Telegram inline buttons."""
    if url and (url.startswith("http://") or url.startswith("https://")):
        return url
    return f"https://t.me/{BOT_USERNAME}"  # fallback

@Client.on_message(filters.private & (filters.document | filters.video | filters.audio), group=4)
async def private_receive_handler(c: Client, m: Message):                    
    user_id = m.from_user.id

    # ✅ Force subscription check
    if FSUB and not await is_user_joined(c, m): 
        return

    # 🔒 User Ban Check
    if await db.is_user_blocked(user_id):
        await m.reply(
            f"🚫 **You are banned from using this bot.**\n\n"
            f"🔄 Contact admin if you think this is a mistake.\n\n@AV_OWNER_BOT"
        )
        return

    # ❌ File sending limit for non-premium users
    if not await db.has_premium_access(user_id):
        is_allowed, remaining_time = await is_user_allowed(user_id)
        if not is_allowed:
            await m.reply_text(
                f"🚫 **You have already sent {MAX_FILES} files!**\n"
                f"Please wait **{remaining_time} seconds** before trying again.",
                quote=True
            )
            return

    file_obj = m.document or m.video or m.audio
    file_name = file_obj.file_name if file_obj.file_name else f"AV_File_{int(time.time())}.mkv"
    file_size = get_size(file_obj.file_size)  # ✅ Pass numeric size

    # ✅ Anti-bot verification for non-premium users
    if not await db.has_premium_access(user_id):
        verified = await av_verification(c, m)
        if not verified:
            return

    try:
        # Forward file to BIN_CHANNEL
        forwarded = await m.forward(chat_id=BIN_CHANNEL)
        hash_str = get_hash(forwarded)

        # ✅ Generate stream and download links using only ID
        stream = f"{URL}watch/{forwarded.id}?hash={hash_str}"
        download = f"{URL}{forwarded.id}?hash={hash_str}"

        # Telegram start link for sharing
        file_link = f"https://t.me/{BOT_USERNAME}?start=file_{forwarded.id}"

        # Save file info in MongoDB
        await db.files.insert_one({
            "user_id": user_id,
            "file_name": file_name,
            "file_size": file_size,
            "file_id": forwarded.id,
            "hash": hash_str,
            "timestamp": time.time()
        })

        # ✅ Send caption with interface like preferred style
        caption_text = f"""✅ Links Generated Successfully!

📂 File Name: {file_name}

📊 File Size: {file_size}

📥 Download: {download}

🎬 Stream: {stream}

📢 Join @KR_BotX for updates!"""

        # Inline buttons
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📥 Download", url=download),
                InlineKeyboardButton("🎬 Stream", url=stream)
            ],
            [
                InlineKeyboardButton("🔗 Share Link", url=file_link)
            ]
        ])

        await m.reply_text(
            caption_text,
            disable_web_page_preview=True,
            reply_markup=buttons
        )

    except FloodWait as e:
        await asyncio.sleep(e.value)
        await c.send_message(BIN_CHANNEL, f"⚠️ FloodWait: {e.value}s from {m.from_user.first_name}")

    except Exception as e:
        await c.send_message(BIN_CHANNEL, f"❌ Error: `{e}`")
