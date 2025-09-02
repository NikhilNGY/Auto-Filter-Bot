# © TechifyBots (Rahul)
import asyncio
import re
import math
import logging
from pyrogram.errors.exceptions.bad_request_400 import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty
from Script import script
from info import MAX_BTN, BIN_CHANNEL, USERNAME, URL, IS_VERIFY, LANGUAGES, AUTH_CHANNEL, SUPPORT_GROUP, QR_CODE, DELETE_TIME, PM_SEARCH, ADMINS
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, WebAppInfo 
from pyrogram import Client, filters, enums
from pyrogram.errors import MessageNotModified
from utils import temp, get_settings, is_check_admin, get_status, get_hash, get_name, get_size, save_group_settings, get_poster, get_status, get_readable_time, get_shortlink, is_req_subscribed, imdb
from database.users_chats_db import db
from database.ia_filterdb import Media, get_search_results, get_bad_files, get_file_details
from fuzzywuzzy import process

# --------------------
# GLOBALS
# --------------------
lock = asyncio.Lock()
logger = logging.getLogger(__name__)

BUTTONS = {}
FILES_ID = {}
CAP = {}


# --------------------
# PRIVATE MESSAGE HANDLER
# --------------------
@Client.on_message(filters.private & filters.text & filters.incoming)
async def pm_search(client, message):
    if PM_SEARCH:
        await auto_filter(client, message)
    else:
        await message.reply_text("⚠️ ꜱᴏʀʀʏ, ɪ ᴄᴀɴ'ᴛ ᴡᴏʀᴋ ɪɴ ᴘᴍ")


# --------------------
# GROUP MESSAGE HANDLER
# --------------------
@Client.on_message(filters.group & filters.text & filters.incoming)
async def group_search(client, message):
    if not message.from_user:  # safety check
        return

    chat_id = message.chat.id
    settings = await get_settings(chat_id)

    if settings["auto_filter"]:

        # Auto filter only when specific languages are found
        if any(lang in message.text.lower() for lang in [
            "hindi", "tamil", "telugu", "malayalam", "kannada", "english", "gujarati"
        ]):
            return await auto_filter(client, message)

        # Ignore commands
        if message.text.startswith("/"):
            return

        # Delete links unless admin
        elif re.findall(r'https?://\S+|www\.\S+|t\.me/\S+', message.text):
            if await is_check_admin(client, chat_id, message.from_user.id):
                return
            await message.delete()
            return await message.reply(
                "<b>‼️ ʟɪɴᴋꜱ ᴀʀᴇ ɴᴏᴛ ᴀʟʟᴏᴡᴇᴅ ʜᴇʀᴇ 🚫</b>"
            )

        # Handle admin mention reports
        elif '@admin' in message.text.lower() or '@admins' in message.text.lower():
            if await is_check_admin(client, chat_id, message.from_user.id):
                return

            admins = []
            async for member in client.get_chat_members(
                chat_id=chat_id, filter=enums.ChatMembersFilter.ADMINISTRATORS
            ):
                if not member.user.is_bot:
                    admins.append(member.user.id)
                    if member.status == enums.ChatMemberStatus.OWNER:
                        try:
                            if message.reply_to_message:
                                sent_msg = await message.reply_to_message.forward(member.user.id)
                                await sent_msg.reply_text(
                                    f"#Attention\n★ User: {message.from_user.mention}\n"
                                    f"★ Group: {message.chat.title}\n\n"
                                    f"★ <a href={message.reply_to_message.link}>Go to message</a>",
                                    disable_web_page_preview=True
                                )
                            else:
                                sent_msg = await message.forward(member.user.id)
                                await sent_msg.reply_text(
                                    f"#Attention\n★ User: {message.from_user.mention}\n"
                                    f"★ Group: {message.chat.title}\n\n"
                                    f"★ <a href={message.link}>Go to message</a>",
                                    disable_web_page_preview=True
                                )
                        except Exception:
                            pass

            hidden_mentions = "".join(f'[\u2064](tg://user?id={uid})' for uid in admins)
            await message.reply_text('<code>Report sent</code>' + hidden_mentions)
            return

        else:
            await auto_filter(client, message)

    else:
        k = await message.reply_text("<b>⚠️ ᴀᴜᴛᴏ ғɪʟᴛᴇʀ ᴍᴏᴅᴇ ɪꜱ ᴏғғ...</b>")
        await asyncio.sleep(10)
        await k.delete()
        try:
            await message.delete()
        except Exception:
            pass


# --------------------
# PAGINATION HANDLER
# --------------------
@Client.on_callback_query(filters.regex(r"^next"))
async def next_page(client, query: CallbackQuery):
    ident, req, key, offset = query.data.split("_")

    if int(req) not in [query.from_user.id, 0]:
        return await query.answer(
            script.ALRT_TXT.format(query.from_user.first_name), show_alert=True
        )

    try:
        offset = int(offset)
    except ValueError:
        offset = 0

    search = BUTTONS.get(key)
    cap = CAP.get(key)

    if not search:
        await query.answer(script.OLD_ALRT_TXT.format(query.from_user.first_name), show_alert=True)
        return

    files, n_offset, total = await get_search_results(search, offset=offset)

    try:
        n_offset = int(n_offset)
    except (ValueError, TypeError):
        n_offset = 0

    if not files:
        return

    temp.FILES_ID[key] = files
    grp_id = query.message.chat.id
    settings = await get_settings(grp_id)
    reqnxt = query.from_user.id if query.from_user else 0
    temp.CHAT[reqnxt] = grp_id

    del_msg = (
        f"\n\n<b>⚠️ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ "
        f"<code>{get_readable_time(DELETE_TIME)}</code> ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs</b>"
        if settings["auto_delete"] else ''
    )

    btn = []
    links = ""

    if settings["link"]:
        for file_num, file in enumerate(files, start=offset + 1):
            links += (
                f"<b>\n\n{file_num}. "
                f"<a href=https://t.me/{temp.U_NAME}?start=file_{grp_id}_{file.file_id}>"
                f"[{get_size(file.file_size)}] "
                f"{' '.join(filter(lambda x: not x.startswith('[') "
                f"and not x.startswith('@') "
                f"and not x.startswith('www.'), file.file_name.split()))}</a></b>"
            )
    else:
        btn = [
            [InlineKeyboardButton(
                text=f"🔗 {get_size(file.file_size)} ≽ {get_name(file.file_name)}",
                url=f'https://t.me/{temp.U_NAME}?start=file_{grp_id}_{file.file_id}'
            )]
            for file in files
        ]

    # Insert navigation buttons
    btn.insert(0, [
        InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ", callback_data=f"send_all#{key}"),
        InlineKeyboardButton("📰 ʟᴀɴɢᴜᴀɢᴇs", callback_data=f"languages#{key}#{req}#{offset}")
    ])

    if 0 < offset <= int(MAX_BTN):
        off_set = 0
    elif offset == 0:
        off_set = None
    else:
        off_set = offset - int(MAX_BTN)

    if n_offset == 0:
        btn.append([
            InlineKeyboardButton("⪻ ʙᴀᴄᴋ", callback_data=f"next_{req}_{key}_{off_set}"),
            InlineKeyboardButton(
                f"ᴘᴀɢᴇ {math.ceil(int(offset) / int(MAX_BTN)) + 1} / {math.ceil(total / int(MAX_BTN))}",
                callback_data="pages"
            )
        ])
    elif off_set is None:
        btn.append([
            InlineKeyboardButton(
                f"{math.ceil(int(offset) / int(MAX_BTN)) + 1} / {math.ceil(total / int(MAX_BTN))}",
                callback_data="pages"
            ),
            InlineKeyboardButton("ɴᴇxᴛ ⪼", callback_data=f"next_{req}_{key}_{n_offset}")
        ])
    else:
        btn.append([
            InlineKeyboardButton("⪻ ʙᴀᴄᴋ", callback_data=f"next_{req}_{key}_{off_set}"),
            InlineKeyboardButton(
                f"{math.ceil(int(offset) / int(MAX_BTN)) + 1} / {math.ceil(total / int(MAX_BTN))}",
                callback_data="pages"
            ),
            InlineKeyboardButton("ɴᴇxᴛ ⪼", callback_data=f"next_{req}_{key}_{n_offset}")
        ])

    if settings["link"]:
        await query.message.edit_text(
            cap + links + del_msg,
            disable_web_page_preview=True,
            parse_mode=enums.ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(btn)
        )
        return

    try:
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(btn))
    except MessageNotModified:
        pass

    await query.answer()


# --------------------
# LANGUAGES HANDLER
# --------------------
@Client.on_callback_query(filters.regex(r"^languages"))
async def languages_cb_handler(client: Client, query: CallbackQuery):
    _, key, req, offset = query.data.split("#")

    if int(req) != query.from_user.id:
        return await query.answer(script.ALRT_TXT, show_alert=True)

    btn = [
        [InlineKeyboardButton(
            text=lang.title(),
            callback_data=f"lang_search#{lang}#{key}#{offset}#{req}"
        )]
        for lang in LANGUAGES
    ]
    btn.append([
        InlineKeyboardButton("⪻ ʙᴀᴄᴋ ᴛᴏ ᴍᴀɪɴ ᴘᴀɢᴇ", callback_data=f"next_{req}_{key}_{offset}")
    ])

    d = await query.message.edit_text(
        "<b>ɪɴ ᴡʜɪᴄʜ ʟᴀɴɢᴜᴀɢᴇ ʏᴏᴜ ᴡᴀɴᴛ, ᴄʜᴏᴏsᴇ ʜᴇʀᴇ 👇</b>",
        reply_markup=InlineKeyboardMarkup(btn),
        disable_web_page_preview=True
    )
    await asyncio.sleep(600)
    try:
        await d.delete()
    except Exception:
        pass


# --------------------
# LANGUAGE SEARCH HANDLER
# --------------------
@Client.on_callback_query(filters.regex(r"^lang_search"))
async def lang_search(client: Client, query: CallbackQuery):
    _, lang, key, offset, req = query.data.split("#")

    if int(req) != query.from_user.id:
        return await query.answer(script.ALRT_TXT, show_alert=True)

    try:
        offset = int(offset)
    except ValueError:
        offset = 0

    search = BUTTONS.get(key)
    cap = CAP.get(key)

    if not search:
        await query.answer(script.OLD_ALRT_TXT.format(query.from_user.first_name), show_alert=True)
        return

    search = search.replace("_", " ")
    files, n_offset, total_results = await get_search_results(search, lang=lang)

    if not files:
        await query.answer(f"sᴏʀʀʏ, '{lang.title()}' ꜰɪʟᴇs ɴᴏᴛ ꜰᴏᴜɴᴅ 😕", show_alert=True)
        return

    temp.FILES_ID[key] = files
    reqnxt = query.from_user.id if query.from_user else 0
    settings = await get_settings(query.message.chat.id)
    group_id = query.message.chat.id

    del_msg = (
        f"\n\n<b>⚠️ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ "
        f"<code>{get_readable_time(DELETE_TIME)}</code> ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs</b>"
        if settings["auto_delete"] else ''
    )

    links = ""
    btn = []

    if settings["link"]:
        for file_num, file in enumerate(files, start=1):
            links += (
                f"<b>\n\n{file_num}. "
                f"<a href=https://t.me/{temp.U_NAME}?start=file_{group_id}_{file.file_id}>"
                f"[{get_size(file.file_size)}] "
                f"{' '.join(filter(lambda x: not x.startswith('[') "
                f"and not x.startswith('@') "
                f"and not x.startswith('www.'), file.file_name.split()))}</a></b>"
            )
    else:
        btn = [
            [InlineKeyboardButton(
                text=f"🔗 {get_size(file.file_size)} ≽ {get_name(file.file_name)}",
                callback_data=f'files#{reqnxt}#{file.file_id}'
            )]
            for file in files
        ]

    # Verification & premium buttons
    if not settings["is_verify"]:
        btn.insert(0, [
            InlineKeyboardButton(
                "♻️ sᴇɴᴅ ᴀʟʟ ♻️",
                url=await get_shortlink(
                    f'https://t.me/{temp.U_NAME}?start=allfiles_{group_id}_{key}', group_id
                )
            ),
            InlineKeyboardButton("🥇ʙᴜʏ🥇", url=f"https://t.me/{temp.U_NAME}?start=buy_premium")
        ])
    else:
        btn.insert(0, [
            InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ ♻️", callback_data=f"send_all#{key}"),
            InlineKeyboardButton("🥇ʙᴜʏ🥇", url=f"https://t.me/{temp.U_NAME}?start=buy_premium")
        ])

    # Pagination
    if n_offset != "":
        btn.append([
            InlineKeyboardButton(f"1/{math.ceil(int(total_results) / MAX_BTN)}", callback_data="buttons"),
            InlineKeyboardButton("ɴᴇxᴛ »", callback_data=f"lang_next#{req}#{key}#{lang}#{n_offset}#{offset}")
        ])

    btn.append([
        InlineKeyboardButton("⪻ ʙᴀᴄᴋ ᴛᴏ ᴍᴀɪɴ ᴘᴀɢᴇ", callback_data=f"next_{req}_{key}_{offset}")
    ])

    await query.message.edit_text(
        cap + links + del_msg,
        disable_web_page_preview=True,
        parse_mode=enums.ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(btn)
                   )

@Client.on_callback_query(filters.regex(r"^lang_next"))
async def lang_next_page(client: Client, query: CallbackQuery):
    # Expected callback_data format:
    # "lang_next#<req>#<key>#<lang>#<l_offset>#<offset>"
    try:
        _, req, key, lang, l_offset, offset = query.data.split("#")
    except ValueError:
        # malformed callback data
        return await query.answer("⚠️ Invalid data", show_alert=True)

    if int(req) != query.from_user.id:
        return await query.answer(script.ALRT_TXT, show_alert=True)

    try:
        l_offset = int(l_offset)
    except (ValueError, TypeError):
        l_offset = 0

    try:
        offset = int(offset)
    except (ValueError, TypeError):
        offset = 0

    search = BUTTONS.get(key)
    cap = CAP.get(key)
    grp_id = query.message.chat.id
    settings = await get_settings(grp_id)

    del_msg = (
        f"\n\n<b>⚠️ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ "
        f"<code>{get_readable_time(DELETE_TIME)}</code> ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs</b>"
        if settings.get("auto_delete") else ''
    )

    if not search:
        await query.answer(f"sᴏʀʀʏ '{lang.title()}' ʟᴀɴɢᴜᴀɢᴇ ꜰɪʟᴇs ɴᴏᴛ ꜰᴏᴜɴᴅ 😕", show_alert=True)
        return

    files, n_offset, total = await get_search_results(search, offset=l_offset, lang=lang)
    if not files:
        # no files found on this page - silently return
        return

    temp.FILES_ID[key] = files

    try:
        n_offset = int(n_offset)
    except (ValueError, TypeError):
        n_offset = 0

    links = ""
    btn = []

    if settings.get('link'):
        for file_num, file in enumerate(files, start=l_offset + 1):
            safe_name = ' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file.file_name.split()))
            links += (
                f"<b>\n\n{file_num}. "
                f"<a href=https://t.me/{temp.U_NAME}?start=file_{grp_id}_{file.file_id}>"
                f"[{get_size(file.file_size)}] {safe_name}</a></b>"
            )
    else:
        # keep callback format consistent with other handlers: 'files#<req>#<file_id>'
        reqnxt = query.from_user.id if query.from_user else 0
        btn = [
            [InlineKeyboardButton(
                text=f"🔗 {get_size(file.file_size)} ≽ {get_name(file.file_name)}",
                callback_data=f'files#{reqnxt}#{file.file_id}'
            )]
            for file in files
        ]

    # top action buttons (send all / buy)
    if not settings.get('is_verify'):
        # use get_shortlink asynchronously for URL
        short_link = await get_shortlink(f'https://t.me/{temp.U_NAME}?start=allfiles_{grp_id}_{key}', grp_id)
        btn.insert(0, [
            InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ ♻️", url=short_link),
            InlineKeyboardButton("🥇ʙᴜʏ🥇", url=f"https://t.me/{temp.U_NAME}?start=buy_premium")
        ])
    else:
        btn.insert(0, [
            InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ ♻️", callback_data=f"send_all#{key}"),
            InlineKeyboardButton("🥇ʙᴜʏ🥇", url=f"https://t.me/{temp.U_NAME}?start=buy_premium")
        ])

    # compute back offsets
    if 0 < l_offset <= int(MAX_BTN):
        b_offset = 0
    elif l_offset == 0:
        b_offset = None
    else:
        b_offset = l_offset - int(MAX_BTN)

    # page buttons
    try:
        total_pages = math.ceil(int(total) / int(MAX_BTN))
        current_page = math.ceil(int(l_offset) / int(MAX_BTN)) + 1
    except Exception:
        total_pages = 1
        current_page = 1

    if n_offset == 0:
        btn.append([
            InlineKeyboardButton("« ʙᴀᴄᴋ", callback_data=f"lang_next#{req}#{key}#{lang}#{b_offset}#{offset}"),
            InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="buttons")
        ])
    elif b_offset is None:
        btn.append([
            InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="buttons"),
            InlineKeyboardButton("ɴᴇxᴛ »", callback_data=f"lang_next#{req}#{key}#{lang}#{n_offset}#{offset}")
        ])
    else:
        btn.append([
            InlineKeyboardButton("« ʙᴀᴄᴋ", callback_data=f"lang_next#{req}#{key}#{lang}#{b_offset}#{offset}"),
            InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="buttons"),
            InlineKeyboardButton("ɴᴇxᴛ »", callback_data=f"lang_next#{req}#{key}#{lang}#{n_offset}#{offset}")
        ])

    # always include a back to main page button
    btn.append([InlineKeyboardButton(text="⪻ ʙᴀᴄᴋ ᴛᴏ ᴍᴀɪɴ ᴘᴀɢᴇ", callback_data=f"next_{req}_{key}_{offset}")])

    # edit the message (use HTML parse mode)
    try:
        await query.message.edit_text(cap + links + del_msg, reply_markup=InlineKeyboardMarkup(btn),
                                      disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML)
    except Exception:
        # if edit fails (e.g., message deleted), ignore
        pass

@Client.on_callback_query(filters.regex(r"^spol"))
async def advantage_spoll_choker(client: Client, query: CallbackQuery):
    # Expected callback_data format: "spol#<id>#<user>"
    try:
        _, movie_id, user = query.data.split('#')
    except ValueError:
        return await query.answer("⚠️ Invalid data", show_alert=True)

    if int(user) != 0 and query.from_user.id != int(user):
        return await query.answer(script.ALRT_TXT, show_alert=True)

    # fetch poster/details (get_poster should be async)
    try:
        movie = await get_poster(movie_id, id=True)
    except Exception:
        movie = None

    if not movie:
        await query.answer("❌ Could not fetch movie data", show_alert=True)
        return

    search = movie.get('title') or movie.get('name') or None
    if not search:
        await query.answer("❌ Movie title not found", show_alert=True)
        return

    await query.answer('ᴄʜᴇᴄᴋɪɴɢ ɪɴ ᴍʏ ᴅᴀᴛᴀʙᴀꜱᴇ 🌚')

    files, offset, total_results = await get_search_results(search)
    if files:
        k = (search, files, offset, total_results)
        # call auto_filter in the same pattern you used elsewhere — some handlers pass different args
        # Here we try to follow your earlier usage: await auto_filter(bot, query, k)
        try:
            await auto_filter(client, query, k)
        except TypeError:
            # fallback if auto_filter expects only (client, message)
            try:
                await auto_filter(client, query.message, k)
            except Exception:
                pass
    else:
        try:
            kmsg = await query.message.edit_text(script.NO_RESULT_TXT)
            await asyncio.sleep(60)
            await kmsg.delete()
        except Exception:
            pass
        # try to remove the replied-to message if exists
        try:
            if query.message.reply_to_message:
                await query.message.reply_to_message.delete()
        except Exception:
            pass

@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    """Universal callback-query handler (safe, modernized)."""
    data = query.data or ""
    user_id = query.from_user.id if query.from_user else None

    # ----------------------
    # Helper to safely get replied user id
    # ----------------------
    def _replied_user_id(msg):
        try:
            if msg and msg.reply_to_message and msg.reply_to_message.from_user:
                return msg.reply_to_message.from_user.id
        except Exception:
            pass
        return None

    # ----------------------
    # close_data: only owner or same user can close
    # ----------------------
    if data == "close_data":
        owner = _replied_user_id(query.message) or user_id or 0
        try:
            if int(owner) != 0 and user_id != int(owner):
                return await query.answer(script.ALRT_TXT, show_alert=True)
        except Exception:
            return await query.answer(script.ALRT_TXT, show_alert=True)

        await query.answer("ᴛʜᴀɴᴋs ꜰᴏʀ ᴄʟᴏsᴇ 🙈")
        # delete the inline message and the replied message if available
        try:
            await query.message.delete()
        except Exception:
            pass
        try:
            if query.message.reply_to_message:
                await query.message.reply_to_message.delete()
        except Exception:
            pass
        return

    # ----------------------
    # checksub#<file_id> : verify subscription and send file
    # ----------------------
    if data.startswith("checksub"):
        parts = data.split("#", 1)
        if len(parts) != 2:
            return await query.answer("⚠️ Invalid callback data", show_alert=True)
        _, file_id = parts

        settings = await get_settings(query.message.chat.id)
        # if auth channel set, ensure user subscribed
        if AUTH_CHANNEL and not await is_req_subscribed(client, query):
            return await query.answer(
                "ɪ ʟɪᴋᴇ ʏᴏᴜʀ sᴍᴀʀᴛɴᴇss ʙᴜᴛ ᴅᴏɴ'ᴛ ʙᴇ ᴏᴜᴇʀsᴍᴀʀᴛ 😒\nꜰɪʀsᴛ ᴊᴏɪɴ ᴏᴜʀ ᴜᴘᴅᴀᴛᴇs ᴄʜᴀɴɴᴇʟ 😒",
                show_alert=True
            )

        # get file details from DB
        files_ = await get_file_details(file_id)
        if not files_:
            return await query.answer('ɴᴏ sᴜᴄʜ ꜰɪʟᴇ ᴇxɪsᴛs 🚫', show_alert=True)

        file = files_[0]
        CAPTION = settings.get('caption', '{file_name}\n{file_size}\n{file_caption}')
        try:
            f_caption = CAPTION.format(
                file_name=file.file_name,
                file_size=get_size(file.file_size),
                file_caption=(file.caption or "")
            )
        except Exception:
            f_caption = f"{file.file_name}\n{get_size(file.file_size)}"

        # send cached media to user (protect_content per settings)
        try:
            await client.send_cached_media(
                chat_id=user_id,
                file_id=file_id,
                caption=f_caption,
                protect_content=bool(settings.get('file_secure', False)),
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton('❌ ᴄʟᴏsᴇ ❌', callback_data='close_data')]]
                )
            )
        except Exception as e:
            logger.exception("send_cached_media failed: %s", e)
            return await query.answer("Failed to send file. It may be deleted.", show_alert=True)
        return

    # ----------------------
    # stream#<file_id> : prepare streaming + download links (premium only)
    # ----------------------
    if data.startswith("stream"):
        # permission: premium only
        if not await db.has_premium_access(user_id):
            d = await query.message.reply_text(
                "<b>💔 ᴛʜɪꜱ ꜰᴇᴀᴛᴜʀᴇ ɪꜱ ᴏɴʟʏ ꜰᴏʀ ʙᴏᴛ ᴘʀᴇᴍɪᴜᴍ ᴜꜱᴇʀꜱ.\n\nɪꜰ ʏᴏᴜ ᴡᴀɴᴛ ʙᴏᴛ ꜱᴜʙꜱᴄʀɪᴘᴛɪᴏɴ ᴛʜᴇɴ ꜱᴇɴᴅ /plan</b>", parse_mode=enums.ParseMode.HTML
            )
            await asyncio.sleep(120)
            try:
                await d.delete()
            except Exception:
                pass
            return

        # get file_id
        parts = data.split("#", 1)
        if len(parts) != 2:
            return await query.answer("⚠️ Invalid callback data", show_alert=True)
        file_id = parts[1]

        try:
            # copy/send to BIN_CHANNEL and get message id
            sent = await client.send_cached_media(chat_id=BIN_CHANNEL, file_id=file_id)
        except Exception as e:
            logger.exception("failed to send to BIN_CHANNEL: %s", e)
            return await query.answer("Failed to prepare streaming. Try later.", show_alert=True)

        # build links
        try:
            nid = sent.id
            h = get_hash(sent)
            online = f"https://{URL}/watch/{nid}?hash={h}"
            download = f"https://{URL}/{nid}?hash={h}"
        except Exception as e:
            logger.exception("failed to build links: %s", e)
            return await query.answer("Internal error building links.", show_alert=True)

        btn = [
            [
                InlineKeyboardButton("ᴡᴀᴛᴄʜ ᴏɴʟɪɴᴇ", url=online),
                InlineKeyboardButton("ꜰᴀsᴛ ᴅᴏᴡɴʟᴏᴀᴅ", url=download),
            ],
            [
                InlineKeyboardButton('🧿 Wᴀᴛᴄʜ ᴏɴ ᴛᴇʟᴇɢʀᴀᴍ 🖥', web_app=WebAppInfo(url=online))
            ]
        ]
        try:
            await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(btn))
        except Exception:
            # If reply markup edit fails, try sending a new message
            try:
                await query.message.reply_text("Links ready:\n" + online)
            except Exception:
                pass
        return

    # ----------------------
    # simple static callback responses
    # ----------------------
    if data == "buttons":
        return await query.answer("ɴᴏ ᴍᴏʀᴇ ᴘᴀɢᴇs 😊", show_alert=True)

    if data == "pages":
        return await query.answer("ᴛʜɪs ɪs ᴘᴀɢᴇs ʙᴜᴛᴛᴏɴ 😅", show_alert=True)

    if data.startswith("lang_art"):
        parts = data.split("#", 1)
        lang = parts[1] if len(parts) == 2 else ""
        return await query.answer(f"ʏᴏᴜ sᴇʟᴇᴄᴛᴇᴅ {lang.title()} ʟᴀɴɢᴜᴀɢᴇ ⚡️", show_alert=True)

    # ----------------------
    # start (main menu)
    # ----------------------
    if data == "start":
        buttons = [
            [InlineKeyboardButton('• Bᴀᴄᴋᴜᴘ Cʜᴀɴɴᴇʟ •', url='https://t.me/sandalwood_kannada_moviesz')],
            [
                InlineKeyboardButton('• Mᴏᴠɪᴇ Gʀᴏᴜᴘ •', url='https://t.me/+x6OfRDdUPrUwZTZl'),
                InlineKeyboardButton('• Mᴀɪɴ Cʜᴀɴɴᴇʟ •', url='https://t.me/+fDkIGNmk5BU5ODVl')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        try:
            await query.message.edit_text(
                text=script.START_TXT.format(query.from_user.mention, get_status(), query.from_user.id),
                reply_markup=reply_markup,
                parse_mode=enums.ParseMode.HTML
            )
        except Exception:
            pass
        return

    # ----------------------
    # features -> submenus
    # ----------------------
    if data == "features":
        buttons = [
            [InlineKeyboardButton('📸 ɪᴍᴀɢᴇ', callback_data='uploader'),
             InlineKeyboardButton('🆎️ ꜰᴏɴᴛ', callback_data='font')],
            [InlineKeyboardButton('⋞ ʙᴀᴄᴋ', callback_data='start')]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        try:
            await query.message.edit_text(text=script.HELP_TXT, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
        except Exception:
            pass
        return

    # other informative pages
    if data == "earn":
        buttons = [
            [InlineKeyboardButton('♻️ ᴄᴜꜱᴛᴏᴍɪᴢᴇ ʏᴏᴜʀ ɢʀᴏᴜᴘ ♻️', callback_data='custom')],
            [InlineKeyboardButton('⋞ ʙᴀᴄᴋ', callback_data='start'), InlineKeyboardButton('sᴜᴘᴘᴏʀᴛ', url=USERNAME)]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        try:
            await query.message.edit_text(text=script.EARN_TEXT.format(temp.B_LINK), reply_markup=reply_markup, disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML)
        except Exception:
            pass
        return

    if data == "uploader":
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton('⋞ ʙᴀᴄᴋ', callback_data='features')]])
        try:
            await query.message.edit_text(text=script.IMGUPL, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
        except Exception:
            pass
        return

    if data == "font":
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton('⋞ ʙᴀᴄᴋ', callback_data='features')]])
        try:
            await query.message.edit_text(text=script.FONT_TXT, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
        except Exception:
            pass
        return

    if data == "custom":
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton('⋞ ʙᴀᴄᴋ', callback_data='earn')]])
        try:
            await query.message.edit_text(text=script.CUSTOM_TEXT, reply_markup=reply_markup, parse_mode=enums.ParseMode.HTML)
        except Exception:
            pass
        return

    # ----------------------
    # buy_premium -> show QR + caption
    # ----------------------
    if data == "buy_premium":
        btn = [
            [InlineKeyboardButton('📸 sᴇɴᴅ sᴄʀᴇᴇɴsʜᴏᴛ 📸', url=USERNAME)],
            [InlineKeyboardButton('🗑 ᴄʟᴏsᴇ 🗑', callback_data='close_data')]
        ]
        try:
            await query.message.reply_photo(photo=QR_CODE, caption=script.PREMIUM_TEXT, reply_markup=InlineKeyboardMarkup(btn), parse_mode=enums.ParseMode.HTML)
        except Exception:
            pass
        return

    # ----------------------
    # setgs#<type>#<status>#<grp_id> -> toggle group settings (admin-only)
    # ----------------------
    if data.startswith("setgs"):
        parts = data.split("#")
        if len(parts) != 4:
            return await query.answer("⚠️ Invalid data", show_alert=True)

        _, set_type, status, grp_id = parts
        try:
            grp_id_int = int(grp_id)
        except Exception:
            return await query.answer("⚠️ Invalid group id", show_alert=True)

        userid = user_id
        if not await is_check_admin(client, grp_id_int, userid):
            return await query.answer(script.ALRT_TXT, show_alert=True)

        # toggle
        new_status = False if status == "True" else True
        await save_group_settings(grp_id_int, set_type, new_status)

        settings = await get_settings(grp_id_int)
        if settings is None:
            try:
                await query.message.edit_text("<b>ꜱᴏᴍᴇᴛʜɪɴɢ ᴡᴇɴᴛ ᴡʀᴏɴɢ</b>")
            except Exception:
                pass
            return

        # Build buttons reflecting settings
        buttons = [
            [InlineKeyboardButton('ᴀᴜᴛᴏ ꜰɪʟᴛᴇʀ', callback_data=f'setgs#auto_filter#{settings["auto_filter"]}#{grp_id}'),
             InlineKeyboardButton('ᴏɴ ✔️' if settings["auto_filter"] else 'ᴏꜰꜰ ✗', callback_data=f'setgs#auto_filter#{settings["auto_filter"]}#{grp_id}')],
            [InlineKeyboardButton('ꜰɪʟᴇ sᴇᴄᴜʀᴇ', callback_data=f'setgs#file_secure#{settings["file_secure"]}#{grp_id}'),
             InlineKeyboardButton('ᴏɴ ✔️' if settings["file_secure"] else 'ᴏꜰꜰ ✗', callback_data=f'setgs#file_secure#{settings["file_secure"]}#{grp_id}')],
            [InlineKeyboardButton('ɪᴍᴅʙ', callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}'),
             InlineKeyboardButton('ᴏɴ ✔️' if settings["imdb"] else 'ᴏꜰꜰ ✗', callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}')],
            [InlineKeyboardButton('sᴘᴇʟʟ ᴄʜᴇᴄᴋ', callback_data=f'setgs#spell_check#{settings["spell_check"]}#{grp_id}'),
             InlineKeyboardButton('ᴏɴ ✔️' if settings["spell_check"] else 'ᴏꜰꜰ ✗', callback_data=f'setgs#spell_check#{settings["spell_check"]}#{grp_id}')],
            [InlineKeyboardButton('ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ', callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{grp_id}'),
             InlineKeyboardButton(f'{get_readable_time(DELETE_TIME)}' if settings["auto_delete"] else 'ᴏꜰꜰ ✗', callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{grp_id}')],
            [InlineKeyboardButton('ʀᴇsᴜʟᴛ ᴍᴏᴅᴇ', callback_data=f'setgs#link#{settings["link"]}#{grp_id}'),
             InlineKeyboardButton('ʟɪɴᴋ' if settings["link"] else 'ʙᴜᴛᴛᴏɴ', callback_data=f'setgs#link#{settings["link"]}#{grp_id}')],
            [InlineKeyboardButton('ꜰɪʟᴇꜱ ᴍᴏᴅᴇ', callback_data=f'setgs#is_verify#{settings.get("is_verify", IS_VERIFY)}#{grp_id}'),
             InlineKeyboardButton('ᴠᴇʀɪꜰʏ' if settings.get("is_verify", IS_VERIFY) else 'ꜱʜᴏʀᴛʟɪɴᴋ', callback_data=f'setgs#is_verify#{settings.get("is_verify", IS_VERIFY)}#{grp_id}')],
            [InlineKeyboardButton('☕️ ᴄʟᴏsᴇ ☕️', callback_data='close_data')]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        try:
            d = await query.message.edit_reply_markup(reply_markup)
            # try to delete after 5 minutes (non-blocking)
            await asyncio.sleep(300)
            try:
                if d:
                    await d.delete()
            except Exception:
                pass
        except Exception:
            pass
        return

    # ----------------------
    # send_all#<key> -> send link or files
    # ----------------------
    if data.startswith("send_all"):
        parts = data.split("#", 1)
        if len(parts) != 2:
            return await query.answer("⚠️ Invalid data", show_alert=True)
        _, key = parts

        # ensure the clicker is the owner of the result
        owner = _replied_user_id(query.message) or user_id or 0
        try:
            if int(owner) != 0 and user_id != int(owner):
                return await query.answer(f"Hello {query.from_user.first_name},\nDon't Click Other Results!", show_alert=True)
        except Exception:
            return await query.answer(script.ALRT_TXT, show_alert=True)

        files = temp.FILES_ID.get(key)
        if not files:
            return await query.answer(script.OLD_ALRT_TXT.format(query.from_user.first_name), show_alert=True)

        # Provide a shortlink to view all files (non-intrusive)
        try:
            url = f"https://t.me/{temp.U_NAME}?start=allfiles_{query.message.chat.id}_{key}"
            await query.answer(url=url)
        except Exception:
            try:
                # fallback: edit message with link
                await query.message.edit_text(f"Open: {url}")
            except Exception:
                pass
        return

    # ----------------------
    # techifybots#<keyword> -> find & delete bad files (admin-only)
    # ----------------------
    if data.startswith("techifybots"):
        parts = data.split("#", 1)
        if len(parts) != 2:
            return await query.answer("⚠️ Invalid data", show_alert=True)
        _, keyword = parts

        try:
            await query.message.edit_text(f"<b>Fᴇᴛᴄʜɪɴɢ Fɪʟᴇs ғᴏʀ ʏᴏᴜʀ ᴏ̨ᴜᴇʀʏ {keyword} ᴏɴ DB... Pʟᴇᴀsᴇ ᴡᴀɪᴛ...</b>", parse_mode=enums.ParseMode.HTML)
            files, total = await get_bad_files(keyword)
            await query.message.edit_text(f"<b>Fᴏᴜɴᴅ {total} Fɪʟᴇs ғᴏʀ ʏᴏᴜʢ ᴏ̨ᴜᴇʀʏ {keyword} !\n\nFɪʟᴇ ᴅᴇʟᴇᴛɪᴏɴ ᴘʀᴏᴄᴇss ᴡɪʟʟ sᴛᴀʀᴛ ɪɴ 5 sᴇᴄᴏɴᴅs!</b>", parse_mode=enums.ParseMode.HTML)
            await asyncio.sleep(5)

            deleted = 0
            async with lock:
                for file in files:
                    file_ids = file.file_id
                    file_name = getattr(file, "file_name", str(file_ids))
                    try:
                        result = await Media.collection.delete_one({'_id': file_ids})
                        if result.deleted_count:
                            logger.info("Deleted %s from DB", file_name)
                            deleted += 1
                            # update progress periodically
                            if deleted % 20 == 0:
                                try:
                                    await query.message.edit_text(f"<b>Progress: deleted {deleted} files ...</b>", parse_mode=enums.ParseMode.HTML)
                                except Exception:
                                    pass
                    except Exception as e:
                        logger.exception("error deleting file: %s", e)
                        # continue on errors
                        continue

            await query.message.edit_text(f"<b>Process Completed. Successfully deleted {deleted} files for query {keyword}.</b>", parse_mode=enums.ParseMode.HTML)
        except Exception as e:
            logger.exception("techifybots error: %s", e)
            try:
                await query.message.edit_text(f"Eʀʀᴏʀ: {e}")
            except Exception:
                pass
        return

    # ----------------------
    # fallback: unknown callback
    # ----------------------
    await query.answer("Unknown action.", show_alert=False)
    return

     ☆☆☆☆☆☆☆♡◇♡■■

async def auto_filter(client, msg, spoll=False):
    if not spoll:
        message = msg
        # Add this null check at the beginning
        if not message.from_user:
            return  # Exit if there's no sender
        
        search = message.text
        chat_id = message.chat.id
        settings = await get_settings(chat_id)
        files, offset, total_results = await get_search_results(search)
        if not files:
            if settings["spell_check"]:
                return await advantage_spell_chok(msg)
            return
    else:
        settings = await get_settings(msg.message.chat.id)
        message = msg.message.reply_to_message  # msg will be callback query
        # Add null check here too
        if not message.from_user:
            return
        
        search, files, offset, total_results = spoll
    
    # Rest of your function remains the same...
    grp_id = message.chat.id
    req = message.from_user.id if message.from_user else 0
    key = f"{message.chat.id}-{message.id}"
    temp.FILES_ID[f"{message.chat.id}-{message.id}"] = files
    pre = 'filep' if settings['file_secure'] else 'file'
    temp.CHAT[message.from_user.id] = message.chat.id  # This line was causing the error
    # ... rest of your function
    settings = await get_settings(message.chat.id)
    del_msg = f"\n\n<b>⚠️ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ <code>{get_readable_time(DELETE_TIME)}</code> ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs</b>" if settings["auto_delete"] else ''
    links = ""
    if settings["link"]:
        btn = []
        for file_num, file in enumerate(files, start=1):
            links += f"""<b>\n\n{file_num}. <a href=https://t.me/{temp.U_NAME}?start=file_{message.chat.id}_{file.file_id}>[{get_size(file.file_size)}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file.file_name.split()))}</a></b>"""
    else:
        btn = [[InlineKeyboardButton(text=f"🔗 {get_size(file.file_size)}≽ {get_name(file.file_name)}", url=f'https://telegram.dog/{temp.U_NAME}?start=file_{message.chat.id}_{file.file_id}'),]
               for file in files
              ]
        
    if offset != "":
        if total_results >= 3:
            if not settings["is_verify"]:
                btn.insert(0,[
                    InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ", url=await get_shortlink(f'https://t.me/{temp.U_NAME}?start=allfiles_{message.chat.id}_{key}', grp_id)),
                    InlineKeyboardButton("📰 ʟᴀɴɢᴜᴀɢᴇs", callback_data=f"languages#{key}#{req}#0")
                ])
            else:
                btn.insert(0,[
                    InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ", callback_data=f"send_all#{key}"),
                    InlineKeyboardButton("📰 ʟᴀɴɢᴜᴀɢᴇs", callback_data=f"languages#{key}#{req}#0")
                ])
        else:
            if not settings["is_verify"]:
                btn.insert(0,[
                    InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ", url=await get_shortlink(f'https://t.me/{temp.U_NAME}?start=allfiles_{message.chat.id}_{key}', grp_id)),
                    InlineKeyboardButton("🥇ʙᴜʏ🥇", url=f"https://t.me/{temp.U_NAME}?start=buy_premium")
                ])
            else:
                btn.insert(0,[
                    InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ", callback_data=f"send_all#{key}"),
                    InlineKeyboardButton("🥇ʙᴜʏ🥇", url=f"https://t.me/{temp.U_NAME}?start=buy_premium")
                ])
    else:
        if total_results >= 3:
            if not settings["is_verify"]:
                btn.insert(0,[
                    InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ", url=await get_shortlink(f'https://t.me/{temp.U_NAME}?start=allfiles_{message.chat.id}_{key}', grp_id)),
                    InlineKeyboardButton("🥇ʙᴜʏ🥇", url=f"https://t.me/{temp.U_NAME}?start=buy_premium")
                ])
            else:
                btn.insert(0,[
                    InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ", callback_data=f"send_all#{key}"),
                    InlineKeyboardButton("🥇ʙᴜʏ🥇", url=f"https://t.me/{temp.U_NAME}?start=buy_premium")
                ])
        else:
            if not settings["is_verify"]:
                btn.insert(0,[
                    InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ", url=await get_shortlink(f'https://t.me/{temp.U_NAME}?start=allfiles_{message.chat.id}_{key}', grp_id))
                ])
            else:
                btn.insert(0,[
                    InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ", callback_data=f"send_all#{key}")
                ])
                         
    if spoll:
        m = await msg.message.edit(f"<b><code>{search}</code> ɪs ꜰᴏᴜɴᴅ ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ ꜰᴏʀ ꜰɪʟᴇs 📫</b>")
        await asyncio.sleep(1.2)
        await m.delete()

    if offset != "":
        BUTTONS[key] = search
        req = message.from_user.id if message.from_user else 0
        btn.append(
            [InlineKeyboardButton(text=f"1/{math.ceil(int(total_results) / int(MAX_BTN))}", callback_data="pages"),
             InlineKeyboardButton(text="ɴᴇxᴛ ⪼", callback_data=f"next_{req}_{key}_{offset}")]
        )
        key = f"{message.chat.id}-{message.id}"
        BUTTONS[key] = search
        req = message.from_user.id if message.from_user else 0
        try:
            offset = int(offset) 
        except:
            offset = int(MAX_BTN)
        
    imdb = await get_poster(search, file=(files[0]).file_name) if settings["imdb"] else None
    TEMPLATE = settings['template']
    if imdb:
        cap = TEMPLATE.format(
            query=search,
            title=imdb['title'],
            votes=imdb['votes'],
            aka=imdb["aka"],
            seasons=imdb["seasons"],
            box_office=imdb['box_office'],
            localized_title=imdb['localized_title'],
            kind=imdb['kind'],
            imdb_id=imdb["imdb_id"],
            cast=imdb["cast"],
            runtime=imdb["runtime"],
            countries=imdb["countries"],
            certificates=imdb["certificates"],
            languages=imdb["languages"],
            director=imdb["director"],
            writer=imdb["writer"],
            producer=imdb["producer"],
            composer=imdb["composer"],
            cinematographer=imdb["cinematographer"],
            music_team=imdb["music_team"],
            distributors=imdb["distributors"],
            release_date=imdb['release_date'],
            year=imdb['year'],
            genres=imdb['genres'],
            poster=imdb['poster'],
            plot=imdb['plot'],
            rating=imdb['rating'],
            url=imdb['url'],
            **locals()
        )
    else:
        cap = f"<b>📂 ʜᴇʀᴇ ɪ ꜰᴏᴜɴᴅ ꜰᴏʀ ʏᴏᴜʀ sᴇᴀʀᴄʜ {search}</b>"
    del_msg = f"\n\n<b>⚠️ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ <code>{get_readable_time(DELETE_TIME)}</code> ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs</b>" if settings["auto_delete"] else ''
    CAP[key] = cap
    if imdb and imdb.get('poster'):
        try:
            if settings['auto_delete']:
                k = await message.reply_photo(photo=imdb.get('poster'), caption=cap[:1024] + links + del_msg, parse_mode=enums.ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btn))
                await asyncio.sleep(DELETE_TIME)
                await k.delete()
                try:
                    await message.delete()
                except:
                    pass
            else:
                await message.reply_photo(photo=imdb.get('poster'), caption=cap[:1024] + links + del_msg, reply_markup=InlineKeyboardMarkup(btn))                    
        except (MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty):
            pic = imdb.get('poster')
            poster = pic.replace('.jpg', "._V1_UX360.jpg")
            if settings["auto_delete"]:
                k = await message.reply_photo(photo=poster, caption=cap[:1024] + links + del_msg, parse_mode=enums.ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btn))
                await asyncio.sleep(DELETE_TIME)
                await k.delete()
                try:
                    await message.delete()
                except:
                    pass
            else:
                await message.reply_photo(photo=poster, caption=cap[:1024] + links + del_msg, parse_mode=enums.ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btn))
        except Exception as e:
            print(e)
            if settings["auto_delete"]:
                k = await message.reply_text(cap + links + del_msg, parse_mode=enums.ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True)
                await asyncio.sleep(DELETE_TIME)
                await k.delete()
                try:
                    await message.delete()
                except:
                    pass
            else:
                await message.reply_text(cap + links + del_msg, parse_mode=enums.ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True)
    else:
        if message.chat.id == SUPPORT_GROUP:
            buttons = [[InlineKeyboardButton('✧ ᴛᴀᴋᴇ ꜰɪʟᴇ ꜰʀᴏᴍ ʜᴇʀᴇ ✧', url="https://telegram.me/KR_PICTURE")]]
            d = await message.reply(text=f"<b>{message.from_user.mention},</b>\n\n({total_results}) ʀᴇsᴜʟᴛ ᴀʀᴇ ꜰᴏᴜɴᴅ ɪɴ ᴍʏ ᴅᴀᴛᴀʙᴀsᴇ ꜰᴏʀ ʏᴏᴜʀ sᴇᴀʀᴄʜ [{search}]\n\n", reply_markup=InlineKeyboardMarkup(buttons))
            await asyncio.sleep(120)
            await message.delete()
            await d.delete()
        else:
            k=await message.reply_text(text=cap + links + del_msg, disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btn), reply_to_message_id=message.id)
            if settings['auto_delete']:
                await asyncio.sleep(DELETE_TIME)
                await k.delete()
                try:
                    await message.delete()
                except:
                    pass

async def ai_spell_check(wrong_name):
    async def search_movie(name):
        search_results = imdb.search_movie(name)
        return [movie['title'] for movie in search_results]

    movie_list = await search_movie(wrong_name)
    if not movie_list:
        return

    for _ in range(5):
        closest_match = process.extractOne(wrong_name, movie_list)
        if not closest_match or closest_match[1] <= 80:
            return
        movie = closest_match[0]
        files, offset, total_results = await get_search_results(movie)
        if files:
            return movie
        movie_list.remove(movie)

    return

async def advantage_spell_chok(message):
    search_text = message.text
    chat_id = message.chat.id

    settings = await get_settings(chat_id)

    cleaned_query = re.sub(
        r"\b(pl(i|e)*?(s|z+|ease|se|ese|(e+)s(e)?)|((send|snd|giv(e)?|gib)(\sme)?)|movie(s)?|new|latest|br((o|u)h?)*|^h(e|a)?(l)*(o)*|mal(ayalam)?|t(h)?amil|file|that|find|und(o)*|kit(t(i|y)?)?o(w)?|thar(u)?(o)*w?|kittum(o)*|aya(k)*(um(o)*)?|full\smovie|any(one)?|with\ssubtitle(s)?)",
        "", search_text, flags=re.IGNORECASE).strip()

    query = f"{cleaned_query} movie"

    try:
        movies = await get_poster(search_text, bulk=True)
    except:
        error_msg = await message.reply(script.I_CUDNT.format(message.from_user.mention))
        await asyncio.sleep(60)
        await error_msg.delete()
        try:
            await message.delete()
        except:
            pass
        return

    if not movies:
        corrected_name = await ai_spell_check(search_text)

        if corrected_name and corrected_name.lower() != search_text.lower():
            try:
                movies = await get_poster(corrected_name, bulk=True)
            except:
                movies = None

        if not movies:
            google_link = search_text.replace(" ", "+")
            button = [[
                InlineKeyboardButton("🔍 ᴄʜᴇᴄᴋ sᴘᴇʟʟɪɴɢ ᴏɴ ɢᴏᴏɢʟᴇ 🔍", url=f"https://www.google.com/search?q={google_link}")
            ]]
            reply = await message.reply_text(script.I_CUDNT.format(search_text), reply_markup=InlineKeyboardMarkup(button))
            await asyncio.sleep(120)
            await reply.delete()
            try:
                await message.delete()
            except:
                pass
            return

    user_id = message.from_user.id if message.from_user else 0
    buttons = [[
        InlineKeyboardButton(text=movie.get('title'), callback_data=f"spol#{movie.movieID}#{user_id}")
    ] for movie in movies]

    buttons.append([
        InlineKeyboardButton("🚫 ᴄʟᴏsᴇ 🚫", callback_data='close_data')
    ])

    final_reply = await message.reply_text(
        text=script.CUDNT_FND.format(message.from_user.mention),
        reply_markup=InlineKeyboardMarkup(buttons),
        reply_to_message_id=message.id
    )
    await asyncio.sleep(120)
    await final_reply.delete()
    try:
        await message.delete()
    except:
        pass
