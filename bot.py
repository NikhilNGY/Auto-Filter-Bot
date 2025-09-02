import asyncio
import logging
import time
from datetime import date, datetime
from typing import Union, Optional, AsyncGenerator

import pytz
from aiohttp import web
from pyrogram import Client, types, __version__
from pyrogram.errors import FloodWait

from database.ia_filterdb import Media
from database.users_chats_db import db
from info import API_ID, API_HASH, ADMINS, BOT_TOKEN, LOG_CHANNEL, PORT, SUPPORT_GROUP
from plugins import web_server, check_expired_premium
from utils import temp

logging.basicConfig(level=logging.INFO)


class Bot(Client):
    def __init__(self):
        super().__init__(
            name="aks",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            sleep_threshold=5,
            workers=150,
            plugins={"root": "plugins"},
        )

    async def start(self):
        st = time.time()
        try:
            # Load banned users/chats from DB
            b_users, b_chats = await db.get_banned()
            temp.BANNED_USERS = b_users or []
            temp.BANNED_CHATS = b_chats or []

            # Try to start the bot
            await super().start()

            # Ensure DB indexes
            await Media.ensure_indexes()

            # Get bot info
            me = await self.get_me()
            temp.ME = me.id
            temp.U_NAME = me.username
            temp.B_NAME = me.first_name
            temp.B_LINK = me.mention
            self.username = "@" + me.username

            # Start premium expiry checker
            self.loop.create_task(check_expired_premium(self))

            logging.info(f"{me.first_name} started successfully ❤️ (v{__version__})")

            # Start web server
            tz = pytz.timezone("Asia/Kolkata")
            today = date.today()
            now = datetime.now(tz)
            timee = now.strftime("%H:%M:%S %p")

            runner = web.AppRunner(await web_server())
            await runner.setup()
            await web.TCPSite(runner, "0.0.0.0", PORT).start()

            # Send restart notifications
            await self.send_message(
                chat_id=LOG_CHANNEL,
                text=(
                    f"<b>{me.mention} ʀᴇsᴛᴀʀᴛᴇᴅ 🤖\n\n"
                    f"📆 ᴅᴀᴛᴇ - <code>{today}</code>\n"
                    f"🕙 ᴛɪᴍᴇ - <code>{timee}</code>\n"
                    f"🌍 ᴛɪᴍᴇ ᴢᴏɴᴇ - <code>Asia/Kolkata</code></b>"
                ),
            )

            await self.send_message(
                chat_id=SUPPORT_GROUP, text=f"<b>{me.mention} ʀᴇsᴛᴀʀᴛᴇᴅ 🤖</b>"
            )

            seconds = int(time.time() - st)
            for admin in ADMINS:
                await self.send_message(
                    chat_id=admin,
                    text=(
                        f"<b>✅ ʙᴏᴛ ʀᴇsᴛᴀʀᴛᴇᴅ\n"
                        f"🕥 ᴛɪᴍᴇ ᴛᴀᴋᴇɴ - <code>{seconds} sᴇᴄᴏɴᴅs</code></b>"
                    ),
                )

        except FloodWait as e:
            logging.warning(f"⚠️ FloodWait: sleeping for {e.value} seconds...")
            await asyncio.sleep(e.value)
            return await self.start()  # retry startup after waiting

    async def stop(self, *args):
        await super().stop()
        logging.info("🛑 Bot stopped.")

    async def iter_messages(
        self,
        chat_id: Union[int, str],
        limit: int,
        offset: int = 0,
    ) -> Optional[AsyncGenerator["types.Message", None]]:
        """Custom message iterator with offset & batch fetching"""
        current = offset
        while current < limit:
            batch_size = min(200, limit - current)
            messages = await self.get_messages(
                chat_id, list(range(current, current + batch_size + 1))
            )
            for message in messages:
                if message:
                    yield message
                current += 1


app = Bot()
app.run()
