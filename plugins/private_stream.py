import time
import asyncio
import urllib.parse
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
from info import URL, BOT_USERNAME, BIN_CHANNEL, CHANNEL, PROTECT_CONTENT, FSUB, MAX_FILES, IS_SHORTLINK, CHANNEL_FILE_CAPTION, HOW_TO_OPEN
from database.users_db import db
from web.utils.file_properties import get_hash
from utils import get_size, get_shortlink
from plugins.avbot import av_verification, is_user_allowed, is_user_joined
from Script import script

def valid_url(url: str) -> str:
    """Ensure URL is safe for Telegram inline buttons."""
    if url and (url.startswith("http://") or url.startswith("https://")):
        return url
    return f"https://t.me/{BOT_USERNAME}"  # fallback safe URL

@Client.on_message(filters.private & (filters.document | filters.video | filters.audio), group=4)
async def private_receive_handler(c: Client, m: Message):                    
    user_id = m.from_user.id

    # ✅ Force subscription check
    if FSUB and not await is_user_joined(c, m): 
        return

    # 🔒 User Ban Check
    is_banned = await db.is_user_blocked(user_id)
    if is_banned:
        await m.reply(
            f"🚫 **You are banned from using this bot.**\n\n"
            f"🔄 **Contact admin if this is a mistake.**\n\n@AV_OWNER_BOT"
        )
        return

    # ❌ File sending limit for non-premium
    if not await db.has_premium_access(user_id):
        is_allowed, remaining_time = await is_user_allowed(user_id)
        if not is_allowed:
            await m.reply_text(
                f"🚫 **You have already sent {MAX_FILES} files!**\nPlease try again after **{remaining_time} seconds**.",
                quote=True
            )
            return

    file_obj = m.document or m.video or m.audio
    file_name = file_obj.file_name if file_obj.file_name else f"AV_File_{int(time.time())}.mkv"
    file_size = get_size(file_obj.file_size)

    # ✅ Anti-bot verification for non-premium
    if not await db.has_premium_access(user_id):
        verified = await av_verification(c, m)
        if not verified:
            return

    try:
        # Forward file to BIN_CHANNEL
        forwarded = await m.forward(chat_id=BIN_CHANNEL)
        hash_str = get_hash(forwarded)

        # Encode filename for URL
        encoded_name = urllib.parse.quote(file_name)

        # Build URLs using original filename
        raw_stream = f"{URL}watch/{forwarded.id}/{encoded_name}?hash={urllib.parse.quote(hash_str)}"
        raw_download = f"{URL}download/{forwarded.id}/{encoded_name}?hash={urllib.parse.quote(hash_str)}"
        raw_file_link = f"https://t.me/{BOT_USERNAME}?start=file_{forwarded.id}"

        # Apply shortlink if enabled
        if IS_SHORTLINK:
            stream = await get_shortlink(raw_stream)
            download = await get_shortlink(raw_download)
            file_link = await get_shortlink(raw_file_link)
        else:
            stream = raw_stream
            download = raw_download
            file_link = raw_file_link

        # Save file info in MongoDB
        await db.files.insert_one({
            "user_id": user_id,
            "file_name": file_name,
            "file_size": file_size,
            "file_id": forwarded.id,
            "hash": hash_str,
            "timestamp": time.time()
        })

        # Reply to user with file links and buttons
        await m.reply_text(
            f"✅ Links Generated Successfully!\n\n"
            f"📂 File Name: {file_name}\n"
            f"📊 File Size: {file_size}\n\n"
            f"📥 Download: {download}\n"
            f"🎬 Stream: {stream}\n\n"
            f"📢 Join {CHANNEL} for updates!",
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("• ꜱᴛʀᴇᴀᴍ •", url=stream),
                    InlineKeyboardButton("• ᴅᴏᴡɴʟᴏᴀᴅ •", url=download)
                ],
                [
                    InlineKeyboardButton("• ɢᴇᴛ ғɪʟᴇ •", url=file_link)
                ]
            ])
        )

    except FloodWait as e:
        await asyncio.sleep(e.value)
        await c.send_message(BIN_CHANNEL, f"⚠️ FloodWait: {e.value}s from {m.from_user.first_name}")
