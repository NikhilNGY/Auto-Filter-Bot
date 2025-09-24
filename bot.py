from pyrogram import Client, types
from database.ia_filterdb import Media
from aiohttp import web
from database.users_chats_db import db
from web import web_app
from info import LOG_CHANNEL, API_ID, API_HASH, BOT_TOKEN, PORT, BIN_CHANNEL, ADMINS, DATABASE_URL
from utils import temp, get_readable_time
from typing import Union, Optional, AsyncGenerator
import time, os, asyncio
from pyrogram.errors import FloodWait

# --- Motor + umongo imports ---
from motor.motor_asyncio import AsyncIOMotorClient
from umongo import MotorAsyncIOInstance

# Initialize Motor and bind Media document
motor_client = AsyncIOMotorClient(DATABASE_URL)
db_instance = MotorAsyncIOInstance(motor_client['AutoFilterDB'])  # replace with your DB name
db_instance.register(Media)

class Bot(Client):
    def __init__(self):
        super().__init__(
            name='Auto_Filter_Bot',
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            plugins={"root": "plugins"}
        )

    async def start(self):
        temp.START_TIME = time.time()
        b_users, b_chats = await db.get_banned()
        temp.BANNED_USERS = b_users
        temp.BANNED_CHATS = b_chats
        await super().start()
        
        if os.path.exists('restart.txt'):
            with open("restart.txt") as file:
                chat_id, msg_id = map(int, file)
            try:
                await self.edit_message_text(chat_id=chat_id, message_id=msg_id, text='Restarted Successfully!')
            except:
                pass
            os.remove('restart.txt')

        temp.BOT = self

        # Ensure indexes using async Motor
        await Media.ensure_indexes()

        me = await self.get_me()
        temp.ME = me.id
        temp.U_NAME = me.username
        temp.B_NAME = me.first_name
        print(f"{me.first_name} is started now 🤗")

        app = web.AppRunner(web_app)
        await app.setup()
        await web.TCPSite(app, "0.0.0.0", PORT).start()

        try:
            await self.send_message(chat_id=LOG_CHANNEL, text=f"<b>{me.mention} Restarted! 🤖</b>")
        except:
            print("Error - Make sure bot admin in LOG_CHANNEL, exiting now")
            exit()

        try:
            m = await self.send_message(chat_id=BIN_CHANNEL, text="Test")
            await m.delete()
        except:
            print("Error - Make sure bot admin in BIN_CHANNEL, exiting now")
            exit()

        for admin in ADMINS:
            await self.send_message(chat_id=admin, text="<b>✅ ʙᴏᴛ ʀᴇsᴛᴀʀᴛᴇᴅ</b>")

    async def stop(self, *args):
        await super().stop()
        print("Bot Stopped! Bye...")

# ---- Async entry point ----
async def main():
    app = Bot()
    try:
        await app.start()
    except FloodWait as e:
        wait_time = get_readable_time(e.value)
        print(f"Flood Wait Occurred. Sleeping for {wait_time} ...")
        await asyncio.sleep(e.value)
        print("Now Ready For Deploying!")
        await app.start()

if __name__ == "__main__":
    asyncio.run(main())
