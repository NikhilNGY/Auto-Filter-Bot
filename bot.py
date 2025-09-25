import asyncio
import os
import time
from typing import AsyncGenerator, Optional, Union

from aiohttp import web
from pyrogram import Client, enums, types
from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from database.ia_filterdb import Media
from database.users_chats_db import db
from info import ADMINS, API_HASH, API_ID, BIN_CHANNEL, BOT_TOKEN, LOG_CHANNEL, PORT
from utils import (
    FILMS_LINK,
    auto_filter,
    get_readable_time,
    get_search_results,
    get_settings,
    is_check_admin,
    save_group_settings,
    script,
    temp,
)
from web import web_app


# ---------------- HTTP Server for UptimeRobot ----------------
async def ping(request):
    return web.Response(text="OK")


async def start_http_server():
    # Add /ping route
    web_app.router.add_get("/ping", ping)
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"HTTP /ping server started on port {PORT}")


# ---------------- Bot Class ----------------
class Bot(Client):
    def __init__(self):
        super().__init__(
            name="Auto_Filter_Bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            plugins={"root": "plugins"},
        )

    async def start(self):
        temp.START_TIME = time.time()
        b_users, b_chats = await db.get_banned()
        temp.BANNED_USERS = b_users
        temp.BANNED_CHATS = b_chats

        await super().start()

        # Handle restart file
        if os.path.exists("restart.txt"):
            with open("restart.txt") as file:
                chat_id, msg_id = map(int, file.read().split())
            try:
                await self.edit_message_text(
                    chat_id=chat_id, message_id=msg_id, text="Restarted Successfully!"
                )
            except:
                pass
            os.remove("restart.txt")

        temp.BOT = self
        await Media.ensure_indexes()
        me = await self.get_me()
        temp.ME = me.id
        temp.U_NAME = me.username
        temp.B_NAME = me.first_name
        print(f"{me.first_name} is started now 🤗")

        # Start HTTP server for UptimeRobot
        await start_http_server()

        # Send startup messages
        try:
            await self.send_message(
                chat_id=LOG_CHANNEL, text=f"<b>{me.mention} Restarted! 🤖</b>"
            )
        except:
            print("Error - Make sure bot is admin in LOG_CHANNEL, exiting now")
            exit()

        try:
            m = await self.send_message(chat_id=BIN_CHANNEL, text="Test")
            await m.delete()
        except:
            print("Error - Make sure bot is admin in BIN_CHANNEL, exiting now")
            exit()

        for admin in ADMINS:
            await self.send_message(chat_id=admin, text="<b>✅ ʙᴏᴛ ʀᴇsᴛᴀʀᴛᴇᴅ</b>")

    async def stop(self, *args):
        await super().stop()
        print("Bot Stopped! Bye...")

    async def iter_messages(
        self: Client, chat_id: Union[int, str], limit: int, offset: int = 0
    ) -> Optional[AsyncGenerator["types.Message", None]]:
        current = offset
        while True:
            new_diff = min(200, limit - current)
            if new_diff <= 0:
                return
            messages = await self.get_messages(
                chat_id, list(range(current, current + new_diff + 1))
            )
            for message in messages:
                yield message
                current += 1


# ---------------- Run the Bot ----------------
app = Bot()


async def main():
    try:
        await app.start()
        print(f"{temp.B_NAME} is running now 🤗")
        # Prevent bot from exiting
        await asyncio.Event().wait()
    finally:
        await app.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except FloodWait as vp:
        wait_time = get_readable_time(vp.value)
        print(f"Flood Wait Occurred, Sleeping For {wait_time}")
        asyncio.run(asyncio.sleep(vp.value))
        print("Resuming bot...")
        asyncio.run(main())
    except Exception as e:
        print(f"Bot crashed: {e}")
