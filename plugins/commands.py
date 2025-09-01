import asyncio
import base64
import random
import string
import re
import requests
from datetime import datetime

import pytz
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from Script import script
from database.ia_filterdb import Media, get_file_details
from database.users_chats_db import db
from info import (
    ADMINS, LOG_CHANNEL, AUTH_CHANNEL, VERIFY_IMG, IS_VERIFY,
    SHORTENER_WEBSITE, SHORTENER_API, SHORTENER_WEBSITE2, SHORTENER_API2,
    SHORTENER_WEBSITE3, SHORTENER_API3, LOG_API_CHANNEL, TWO_VERIFY_GAP,
    THREE_VERIFY_GAP, TUTORIAL, TUTORIAL2, TUTORIAL3, QR_CODE, DELETE_TIME
)
from utils import (
    get_settings, save_group_settings, is_subscribed, get_size,
    get_shortlink, is_check_admin, get_status, temp, get_readable_time
)


async def send_delete_later(client, chat_id, message, delay: int = 600):
    """Helper to delete message after a delay"""
    await asyncio.sleep(delay)
    await message.delete()


# -------------------- START COMMAND -------------------- #
@Client.on_message(filters.command("start") & filters.incoming)
async def start(client: Client, message):
    user = message.from_user
    user_id = user.id
    cmd = message.command

    # Handle notcopy verification flow
    if len(cmd) == 2 and cmd[1].startswith("notcopy"):
        _, userid, verify_id, file_id = cmd[1].split("_", 3)
        user_id = int(userid)
        grp_id = temp.CHAT.get(user_id, 0)
        settings = await get_settings(grp_id)
        verify_info = await db.get_verify_id_info(user_id, verify_id)
        if not verify_info or verify_info["verified"]:
            await message.reply("<b>ʟɪɴᴋ ᴇxᴘɪʀᴇᴅ. ᴛʀʏ ᴀɢᴀɪɴ...</b>")
            return

        ist = pytz.timezone("Asia/Kolkata")
        if await db.user_verified(user_id):
            key = "third_time_verified"
        else:
            key = "second_time_verified" if await db.is_user_verified(user_id) else "last_verified"

        now = datetime.now(ist)
        await db.update_notcopy_user(user_id, {key: now})
        await db.update_verify_id_info(user_id, verify_id, {"verified": True})

        num = {"last_verified": 1, "second_time_verified": 2, "third_time_verified": 3}[key]
        msg = {
            "last_verified": script.VERIFY_COMPLETE_TEXT,
            "second_time_verified": script.SECOND_VERIFY_COMPLETE_TEXT,
            "third_time_verified": script.THIRDT_VERIFY_COMPLETE_TEXT
        }[key]

        # Log verification
        await client.send_message(
            settings['log'],
            script.VERIFIED_LOG_TEXT.format(user.mention, user_id, now.strftime("%d %B %Y"), num)
        )

        btn = [[
            InlineKeyboardButton(
                "✅ ᴄʟɪᴄᴋ ʜᴇʀᴇ ᴛᴏ ɢᴇᴛ ꜰɪʟᴇ ✅",
                url=f"https://telegram.me/{temp.U_NAME}?start=file_{grp_id}_{file_id}"
            )
        ]]
        await message.reply_photo(
            photo=VERIFY_IMG,
            caption=msg.format(user.mention),
            reply_markup=InlineKeyboardMarkup(btn),
            parse_mode=enums.ParseMode.HTML
        )
        return

    # Handle group chats
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        status = get_status()
        reply = await message.reply_text(f"<b>🔥 ʏᴇs {status},\nʜᴏᴡ ᴄᴀɴ ɪ ʜᴇʟᴘ ʏᴏᴜ??</b>")
        await asyncio.sleep(600)
        await reply.delete()
        await message.delete()

        # Add new group to DB
        if str(message.chat.id).startswith("-100") and not await db.get_chat(message.chat.id):
            total = await client.get_chat_members_count(message.chat.id)
            group_link = await message.chat.export_invite_link()
            user_mention = user.mention if user else "Dear"
            await client.send_message(
                LOG_CHANNEL,
                script.NEW_GROUP_TXT.format(message.chat.title, message.chat.id,
                                            message.chat.username, group_link, total, user_mention)
            )
            await db.add_chat(message.chat.id, message.chat.title)
        return

    # Add new user to DB
    if not await db.is_user_exist(user.id):
        await db.add_user(user.id, user.first_name)
        await client.send_message(LOG_CHANNEL, script.NEW_USER_TXT.format(user.id, user.mention))

    # Normal start message
    if len(cmd) == 1:
        buttons = [[
            InlineKeyboardButton('• Bᴀᴄᴋᴜᴘ Cʜᴀɴɴᴇʟ •', url='https://t.me/sandalwood_kannada_moviesz')
        ], [
            InlineKeyboardButton('• Mᴏᴠɪᴇ Gʀᴏᴜᴘ •', url='https://t.me/+x6OfRDdUPrUwZTZl'),
            InlineKeyboardButton('• Mᴀɪɴ Cʜᴀɴɴᴇʟ •', url='https://t.me/+fDkIGNmk5BU5ODVl')
        ]]
        await message.reply_text(
            script.START_TXT.format(user.mention, get_status(), user.id),
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=enums.ParseMode.HTML
        )
        return

    # Handle shortlinks / verification / file access
    await handle_start_links(client, message, cmd[1])


# -------------------- SETTINGS COMMAND -------------------- #
@Client.on_message(filters.command("settings"))
async def settings(client, message):
    user_id = message.from_user.id
    if not user_id:
        return await message.reply("<b>💔 ʏᴏᴜ ᴀʀᴇ ᴀɴᴏɴʏᴍᴏᴜꜱ...</b>")

    if message.chat.type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply("<code>ᴜꜱᴇ ɪɴ ɢʀᴏᴜᴘ</code>")

    grp_id = message.chat.id
    if not await is_check_admin(client, grp_id, user_id):
        return await message.reply('<b>ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴅᴍɪɴ</b>')

    settings = await get_settings(grp_id)
    if not settings:
        return await message.reply('<b>ꜱᴏᴍᴇᴛʜɪɴɢ ᴡᴇɴᴛ ᴡʀᴏɴɢ</b>')

    buttons = [
        [InlineKeyboardButton('ᴀᴜᴛᴏ ꜰɪʟᴛᴇʀ', callback_data=f'setgs#auto_filter#{settings["auto_filter"]}#{grp_id}'),
         InlineKeyboardButton('ᴏɴ ✔️' if settings["auto_filter"] else 'ᴏꜰꜰ ✗', callback_data=f'setgs#auto_filter#{settings["auto_filter"]}#{grp_id}')],
        # ... repeat for all other settings
        [InlineKeyboardButton('☕️ ᴄʟᴏsᴇ ☕️', callback_data='close_data')]
    ]
    await message.reply_text(
        f"ᴄʜᴀɴɢᴇ ʏᴏᴜʀ sᴇᴛᴛɪɴɢs ꜰᴏʀ <b>'{message.chat.title}'</b>",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=enums.ParseMode.HTML
    )


# -------------------- TEMPLATE / CAPTION COMMANDS -------------------- #
@Client.on_message(filters.command("template"))
async def save_template(client, message):
    if message.chat.type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply("<b>Use in group only</b>")

    grp_id = message.chat.id
    if not await is_check_admin(client, grp_id, message.from_user.id):
        return await message.reply("<b>You are not admin</b>")

    try:
        template = message.text.split(" ", 1)[1]
    except IndexError:
        return await message.reply("<b>Template missing</b
