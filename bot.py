import os, sys, glob, pytz, asyncio, logging, importlib
from pathlib import Path
from pyrogram import Client, idle, filters
from pyrogram.types import Message
import re

# Dont Remove My Credit @AV_BOTz_UPDATE 
# This Repo Is By @BOT_OWNER26 
# For Any Kind Of Error Ask Us In Support Group @AV_SUPPORT_GROUP

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("aiohttp").setLevel(logging.ERROR)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("aiohttp.web").setLevel(logging.ERROR)

from info import *
from typing import Union, Optional, AsyncGenerator
from Script import script 
from datetime import date, datetime 
from aiohttp import web
from web import web_server, check_expired_premium
from web.server import Webavbot
from utils import temp, ping_server
from web.server.clients import initialize_clients
from database.users_db import db  # MongoDB

# ---------------- Load Plugins ---------------- #
ppath = "plugins/*.py"
files = glob.glob(ppath)
Webavbot.start()
loop = asyncio.get_event_loop()

async def start():
    print('\n')
    print('Initializing Your Bot')
    bot_info = await Webavbot.get_me()
    await initialize_clients()

    for name in files:
        with open(name) as a:
            patt = Path(a.name)
            plugin_name = patt.stem.replace(".py", "")
            plugins_dir = Path(f"plugins/{plugin_name}.py")
            import_path = "plugins.{}".format(plugin_name)
            spec = importlib.util.spec_from_file_location(import_path, plugins_dir)
            load = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(load)
            sys.modules["plugins." + plugin_name] = load
            print("Imported => " + plugin_name)

    # ---------------- Register /start file_<id> Handler ---------------- #
    @Webavbot.on_message(filters.private & filters.regex(r'^/start file_(\d+)$'))
    async def send_file_handler(c: Webavbot, m: Message):
        match = re.match(r'^/start file_(\d+)$', m.text)
        if not match:
            return
        file_id = int(match.group(1))

        # Fetch file info from MongoDB
        file_data = await db.files.find_one({"file_id": file_id})
        if not file_data:
            await m.reply_text("❌ File not found or deleted!")
            return

        try:
            await c.send_document(
                chat_id=m.chat.id,
                document=file_data['file_id'],        # Telegram file_id
                file_name=file_data['file_name'],     # ✅ Preserve original filename
                caption=f"📂 File Name: {file_data['file_name']}\n📊 File Size: {file_data['file_size']}",
                disable_notification=True
            )
        except Exception as e:
            await m.reply_text(f"❌ Failed to send file: {e}")

    # ---------------- Heroku / Ping / Uptime Tasks ---------------- #
    if ON_HEROKU:
        asyncio.create_task(ping_server())

    me = await Webavbot.get_me()
    temp.BOT = Webavbot
    temp.ME = me.id
    temp.U_NAME = me.username
    temp.B_NAME = me.first_name

    tz = pytz.timezone('Asia/Kolkata')
    today = date.today()
    now = datetime.now(tz)
    time_now = now.strftime("%H:%M:%S %p")

    Webavbot.loop.create_task(check_expired_premium(Webavbot))

    # Send startup messages
    await Webavbot.send_message(chat_id=LOG_CHANNEL, text=script.RESTART_TXT.format(today, time_now))
    await Webavbot.send_message(chat_id=ADMINS[0], text='<b>ʙᴏᴛ ʀᴇsᴛᴀʀᴛᴇᴅ !!</b>')
    await Webavbot.send_message(chat_id=SUPPORT_GROUP, text=f"<b>{me.mention} ʀᴇsᴛᴀʀᴛᴇᴅ 🤖</b>")

    # ---------------- Start Web Server ---------------- #
    app = web.AppRunner(await web_server())
    await app.setup()
    bind_address = "0.0.0.0"
    await web.TCPSite(app, bind_address, PORT).start()

    await idle()

# ---------------- Main ---------------- #
if __name__ == '__main__':
    try:
        loop.run_until_complete(start())
    except KeyboardInterrupt:
        logging.info('----------------------- Service Stopped -----------------------')
