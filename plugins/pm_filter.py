# © TechifyBots (Rahul)
import asyncio
import math
import re
import logging
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, WebAppInfo
from pyrogram.errors import MessageNotModified
from Script import script
from info import (
    MAX_BTN, BIN_CHANNEL, USERNAME, URL, IS_VERIFY, LANGUAGES,
    AUTH_CHANNEL, SUPPORT_GROUP, QR_CODE, DELETE_TIME, PM_SEARCH, ADMINS
)
from utils import (
    temp, get_settings, is_check_admin, get_status, get_hash, get_name,
    get_size, save_group_settings, get_poster, get_readable_time, get_shortlink,
    is_req_subscribed, imdb
)
from database.users_chats_db import db
from database.ia_filterdb import Media, get_search_results, get_bad_files, get_file_details

# Logging
logger = logging.getLogger(__name__)
lock = asyncio.Lock()

# Global dictionaries
BUTTONS = {}
FILES_ID = {}
CAP = {}


# ------------------- PM SEARCH -------------------
@Client.on_message(filters.private & filters.text & filters.incoming)
async def pm_search(client, message):
    if PM_SEARCH:
        await auto_filter(client, message)
    else:
        await message.reply_text(
            "<strong><blockquote>Fʀɪᴇɴᴅꜱ.......🖤\nWᴇ Hᴀᴠᴇ Aʟʀᴇᴀᴅʏ Lᴏꜱᴛ Mᴀɴʏ Cʜᴀɴɴᴇʟꜱ Dᴜᴇ Tᴏ Cᴏᴘʏʀɪɢʜᴛ... Sᴏ Jᴏɪɴ Uꜱ Bʏ Gɪᴠɪɴɢ Yᴏᴜʀ Sᴜᴘᴘᴏʀᴛ 🙏\nTeam: @KR_Picture</blockquote></strong>"
        )


# ------------------- GROUP SEARCH -------------------
@Client.on_message(filters.group & filters.text & filters.incoming)
async def group_search(client, message):
    chat_id = message.chat.id
    settings = await get_settings(chat_id)

    if not settings["auto_filter"]:
        k = await message.reply_text('<b>⚠️ ᴀᴜᴛᴏ ғɪʟᴛᴇʀ ᴍᴏᴅᴇ ɪꜱ ᴏꜰꜰ...</b>')
        await asyncio.sleep(10)
        await k.delete()
        try:
            await message.delete()
        except:
            pass
        return

    # Skip commands
    if message.text.startswith("/"):
        return

    # Detect links
    if re.findall(r'https?://\S+|www\.\S+|t\.me/\S+', message.text):
        if await is_check_admin(client, chat_id, message.from_user.id):
            return
        await message.delete()
        await message.reply(
            '<b>‼️ Links are not allowed here 🚫\nTeam: @KR_Picture</b>'
        )
        return

    # Detect @admin mentions
    if '@admin' in message.text.lower() or '@admins' in message.text.lower():
        if await is_check_admin(client, chat_id, message.from_user.id):
            return

        admins = [
            member.user.id
            async for member in client.get_chat_members(chat_id, filter=enums.ChatMembersFilter.ADMINISTRATORS)
            if not member.user.is_bot
        ]

        if message.reply_to_message:
            for admin_id in admins:
                try:
                    sent_msg = await message.reply_to_message.forward(admin_id)
                    await sent_msg.reply_text(
                        f"#Attention\n★ User: {message.from_user.mention}\n★ Group: {message.chat.title}\n\n★ <a href={message.reply_to_message.link}>Go to message</a>",
                        disable_web_page_preview=True
                    )
                except:
                    pass
        else:
            for admin_id in admins:
                try:
                    sent_msg = await message.forward(admin_id)
                    await sent_msg.reply_text(
                        f"#Attention\n★ User: {message.from_user.mention}\n★ Group: {message.chat.title}\n\n★ <a href={message.link}>Go to message</a>",
                        disable_web_page_preview=True
                    )
                except:
                    pass

        hidden_mentions = (f'[\u2064](tg://user?id={user_id})' for user_id in admins)
        await message.reply_text('<code>Report sent</code>' + ''.join(hidden_mentions))
        return

    await auto_filter(client, message)


# ------------------- CALLBACK HANDLERS -------------------
@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    data = query.data

    if data == "close_data":
        await close_message(client, query)
    elif data.startswith("checksub"):
        await handle_checksub(client, query)
    elif data.startswith("stream"):
        await handle_stream(client, query)
    elif data.startswith("send_all"):
        await handle_send_all(client, query)
    elif data.startswith("setgs"):
        await handle_settings(client, query)
    elif data.startswith("techifybots"):
        await handle_delete_files(client, query)
    elif data == "start":
        await show_start_page(client, query)
    elif data == "features":
        await show_features(client, query)
    elif data in ["uploader", "font", "custom", "buy_premium", "earn"]:
        await show_custom_pages(client, query)
    elif data.startswith("languages"):
        await handle_languages(client, query)
    elif data.startswith("lang_search"):
        await handle_lang_search(client, query)
    elif data.startswith("lang_next"):
        await handle_lang_next(client, query)
    elif data == "buttons":
        await query.answer("No more pages 😊", show_alert=True)
    elif data == "pages":
        await query.answer("This is a page button 😅")
    elif data.startswith("lang_art"):
        _, lang = data.split("#")
        await query.answer(f"You selected {lang.title()} language ⚡️", show_alert=True)


# ------------------- AUTO FILTER -------------------
async def auto_filter(client, msg, spoll=False):
    """
    Handles search & auto-filter in PM or Group.
    """
    if not spoll:
        message = msg
        search = message.text
        settings = await get_settings(message.chat.id)
        files, offset, total_results = await get_search_results(search)
        if not files and settings["spell_check"]:
            return await advantage_spell_chok(msg)
        elif not files:
            return
    else:
        settings = await get_settings(msg.message.chat.id)
        message = msg.message
        search, files, offset, total_results = spoll

    key = f"{message.chat.id}-{message.id}"
    temp.FILES_ID[key] = files
    grp_id = message.chat.id
    req = message.from_user.id if message.from_user else 0
    del_msg = f"\n\n<b>⚠️ This message will auto-delete after <code>{get_readable_time(DELETE_TIME)}</code> to avoid copyright issues.\nTeam: @KR_Picture</b>" if settings["auto_delete"] else ''

    # Buttons or links
    if settings["link"]:
        text_links = ""
        for i, file in enumerate(files, start=1):
            text_links += f"<b>\n\n{i}. <a href=https://t.me/{temp.U_NAME}?start=file_{grp_id}_{file.file_id}>[{get_size(file.file_size)}] {get_name(file.file_name)}</a></b>"
        await message.reply_text(text_links + del_msg, disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML)
    else:
        btn = [
            [InlineKeyboardButton(f"🔗 {get_size(file.file_size)}≽ {get_name(file.file_name)}",
                                  url=f'https://telegram.dog/{temp.U_NAME}?start=file_{grp_id}_{file.file_id}')]
            for file in files
        ]

        if total_results >= 3:
            if not settings["is_verify"]:
                btn.insert(0, [
                    InlineKeyboardButton("♻️ Send All", url=await get_shortlink(f'https://t.me/{temp.U_NAME}?start=allfiles_{grp_id}_{key}', grp_id)),
                    InlineKeyboardButton("📰 Languages", callback_data=f"languages#{key}#{req}#0")
                ])
            else:
                btn.insert(0, [
                    InlineKeyboardButton("♻️ Send All", callback_data=f"send_all#{key}"),
                    InlineKeyboardButton("📰 Languages", callback_data=f"languages#{key}#{req}#0")
                ])
        else:
            if not settings["is_verify"]:
                btn.insert(0, [InlineKeyboardButton("♻️ Send All", url=await get_shortlink(f'https://t.me/{temp.U_NAME}?start=allfiles_{grp_id}_{key}', grp_id))])
            else:
                btn.insert(0, [InlineKeyboardButton("♻️ Send All", callback_data=f"send_all#{key}")])

        await message.reply_text(
            script.START_TXT.format(message.from_user
