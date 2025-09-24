import asyncio
import urllib.parse
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
from info import BIN_CHANNEL, URL, CHANNEL, BOT_USERNAME, IS_SHORTLINK, CHANNEL_FILE_CAPTION, HOW_TO_OPEN
from web.utils.file_properties import get_hash
from utils import get_size, get_shortlink
from database.users_db import db

@Client.on_message(filters.channel & (filters.document | filters.video) & ~filters.forwarded, group=-1)
async def channel_receive_handler(bot: Client, broadcast: Message):
    try:
        chat_id = broadcast.chat.id

        # 🚫 Check if channel is banned
        if str(chat_id).startswith("-100"):
            is_banned = await db.is_channel_blocked(chat_id)
            if is_banned:
                try:
                    await bot.send_message(
                        chat_id,
                        f"🚫 **Tʜɪꜱ ᴄʜᴀɴɴᴇʟ ɪꜱ ʙᴀɴɴᴇᴅ ғʀᴏᴍ ᴜꜱɪɴɢ ᴛʜᴇ ʙᴏᴛ.**\n\n"
                        f"🔄 **Cᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ ɪꜰ ʏᴏᴜ ᴛʜɪɴᴋ ᴛʜɪꜱ ɪꜱ ᴀ ᴍɪꜱᴛᴀᴋᴇ.**\n\n@AV_OWNER_BOT"
                    )
                except:
                    pass
                await bot.leave_chat(chat_id)
                return

        file = broadcast.document or broadcast.video
        if not file:
            return

        # ✅ Original filename and size
        file_name = file.file_name if file.file_name else f"Channel_File_{int(time.time())}.mkv"
        file_size = get_size(file.file_size)

        # Forward to BIN_CHANNEL
        msg = await broadcast.forward(chat_id=BIN_CHANNEL)
        hash_str = get_hash(msg)

        # Safe URL encoding
        safe_file_name = urllib.parse.quote(file_name)
        raw_stream = f"{URL}watch/{msg.id}/{safe_file_name}?hash={urllib.parse.quote(hash_str)}"
        raw_download = f"{URL}{msg.id}/{safe_file_name}?hash={urllib.parse.quote(hash_str)}"
        raw_file_link = f"https://t.me/{BOT_USERNAME}?start=file_{msg.id}"

        # Shortlink handling
        if IS_SHORTLINK:
            stream = await get_shortlink(raw_stream)
            download = await get_shortlink(raw_download)
            file_link = await get_shortlink(raw_file_link)
        else:
            stream = raw_stream
            download = raw_download
            file_link = raw_file_link

        # Update channel message caption
        new_caption = CHANNEL_FILE_CAPTION.format(CHANNEL, file_name)
        buttons_list = [
            [
                InlineKeyboardButton("• ꜱᴛʀᴇᴀᴍ •", url=stream),
                InlineKeyboardButton("• ᴅᴏᴡɴʟᴏᴀᴅ •", url=download)
            ],
            [
                InlineKeyboardButton("• ᴄʜᴇᴄᴋ ʜᴇʀᴇ ᴛᴏ ɢᴇᴛ ғɪʟᴇ •", url=file_link)
            ]
        ]
        if IS_SHORTLINK:
            buttons_list.append([InlineKeyboardButton("• ʜᴏᴡ ᴛᴏ ᴏᴘᴇɴ •", url=HOW_TO_OPEN)])

        buttons = InlineKeyboardMarkup(buttons_list)

        await bot.edit_message_caption(
            chat_id=broadcast.chat.id,
            message_id=broadcast.id,
            caption=new_caption,
            reply_markup=buttons,
            parse_mode=enums.ParseMode.HTML
        )

    except asyncio.exceptions.TimeoutError:
        print("Request Timed Out! Retrying...")
        await asyncio.sleep(5)
        await channel_receive_handler(bot, broadcast)

    except FloodWait as w:
        print(f"Sleeping for {w.value}s due to FloodWait")
        await asyncio.sleep(w.value)

    except Exception as e:
        await bot.send_message(chat_id=BIN_CHANNEL, text=f"❌ **Error:** `{e}`", disable_web_page_preview=True)
        print(f"❌ Can't edit channel message! Error: {e}")
