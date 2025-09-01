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

lock = asyncio.Lock()

logger = logging.getLogger(__name__)

BUTTONS = {}
FILES_ID = {}
CAP = {}


@Client.on_message(filters.private & filters.text & filters.incoming)
async def pm_search(client, message):
    if PM_SEARCH:
        await auto_filter(client, message)  
    else:
        await message.reply_text("⚠️ ꜱᴏʀʀʏ ɪ ᴄᴀɴ'ᴛ ᴡᴏʀᴋ ɪɴ ᴘᴍ ᴛᴇᴀᴍ: @KR_Picture")
    
@Client.on_message(filters.group & filters.text & filters.incoming)
async def group_search(client, message):
    chat_id = message.chat.id
    settings = await get_settings(chat_id)
    if settings["auto_filter"]:  
        if 'hindi' in message.text.lower() or 'tamil' in message.text.lower() or 'telugu' in message.text.lower() or 'malayalam' in message.text.lower() or 'kannada' in message.text.lower() or 'english' in message.text.lower() or 'gujarati' in message.text.lower(): 
            return await auto_filter(client, message)

        if message.text.startswith("/"):
            return
        
        elif re.findall(r'https?://\S+|www\.\S+|t\.me/\S+', message.text):
            if await is_check_admin(client, message.chat.id, message.from_user.id):
                return
            await message.delete()
            return await message.reply('<b>‼️ ᴡʜʏ ʏᴏᴜ ꜱᴇɴᴅ ʜᴇʀᴇ ʟɪɴᴋ\nʟɪɴᴋ ɴᴏᴛ ᴀʟʟᴏᴡᴇᴅ ʜᴇʀᴇ 🚫 ᴛᴇᴀᴍ: @KR_Picture</b>')

        elif '@admin' in message.text.lower() or '@admins' in message.text.lower():
            if await is_check_admin(client, message.chat.id, message.from_user.id):
                return
            admins = []
            async for member in client.get_chat_members(chat_id=message.chat.id, filter=enums.ChatMembersFilter.ADMINISTRATORS):
                if not member.user.is_bot:
                    admins.append(member.user.id)
                    if member.status == enums.ChatMemberStatus.OWNER:
                        if message.reply_to_message:
                            try:
                                sent_msg = await message.reply_to_message.forward(member.user.id)
                                await sent_msg.reply_text(f"#Attention\n★ User: {message.from_user.mention}\n★ Group: {message.chat.title}\n\n★ <a href={message.reply_to_message.link}>Go to message</a>", disable_web_page_preview=True)
                            except:
                                pass
                        else:
                            try:
                                sent_msg = await message.forward(member.user.id)
                                await sent_msg.reply_text(f"#Attention\n★ User: {message.from_user.mention}\n★ Group: {message.chat.title}\n\n★ <a href={message.link}>Go to message</a>", disable_web_page_preview=True)
                            except:
                                pass
            hidden_mentions = (f'[\u2064](tg://user?id={user_id})' for user_id in admins)
            await message.reply_text('<code>Report sent</code>' + ''.join(hidden_mentions))
            return
        else:
            await auto_filter(client, message)   
    else:
        k=await message.reply_text('<b>⚠️ ᴀᴜᴛᴏ ғɪʟᴛᴇʀ ᴍᴏᴅᴇ ɪꜱ ᴏғғ...</b>')
        await asyncio.sleep(10)
        await k.delete()
        try:
            await message.delete()
        except:
            pass
                
@Client.on_callback_query(filters.regex(r"^next"))
async def next_page(bot, query):
    ident, req, key, offset = query.data.split("_")
    if int(req) not in [query.from_user.id, 0]:
        return await query.answer(script.ALRT_TXT.format(query.from_user.first_name), show_alert=True)
    try:
        offset = int(offset)
    except:
        offset = 0
    search = BUTTONS.get(key)
    cap = CAP.get(key)
    if not search:
        await query.answer(script.OLD_ALRT_TXT.format(query.from_user.first_name),show_alert=True)
        return
    files, n_offset, total = await get_search_results(search, offset=offset)
    try:
        n_offset = int(n_offset)
    except:
        n_offset = 0
    if not files:
        return
    temp.FILES_ID[key] = files
    grp_id = query.message.chat.id
    settings = await get_settings(query.message.chat.id)
    reqnxt  = query.from_user.id if query.from_user else 0
    temp.CHAT[query.from_user.id] = query.message.chat.id
    del_msg = f"\n\n<b>⚠️ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ <code>{get_readable_time(DELETE_TIME)}</code> ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs Tᴇᴀᴍ: @KR_Picture</b>" if settings["auto_delete"] else ''
    links = ""
    if settings["link"]:
        btn = []
        for file_num, file in enumerate(files, start=offset+1):
            links += f"""<b>\n\n{file_num}. <a href=https://t.me/{temp.U_NAME}?start=file_{query.message.chat.id}_{file.file_id}>[{get_size(file.file_size)}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file.file_name.split()))}</a></b>"""
    else:
        btn = [[InlineKeyboardButton(text=f"🔗 {get_size(file.file_size)}≽ {get_name(file.file_name)}", url=f'https://telegram.dog/{temp.U_NAME}?start=file_{query.message.chat.id}_{file.file_id}'),]
                for file in files
              ]

    if not settings["is_verify"]:
        btn.insert(0,[
            InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ", callback_data=f"send_all#{key}"),
            InlineKeyboardButton("📰 ʟᴀɴɢᴜᴀɢᴇs", callback_data=f"languages#{key}#{req}#{offset}")
        ])


    else:
        btn.insert(0,[
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

        btn.append(
            [InlineKeyboardButton("⪻ ʙᴀᴄᴋ", callback_data=f"next_{req}_{key}_{off_set}"),
             InlineKeyboardButton(f"ᴘᴀɢᴇ {math.ceil(int(offset) / int(MAX_BTN)) + 1} / {math.ceil(total / int(MAX_BTN))}", callback_data="pages")]
        )
    elif off_set is None:
        btn.append(
            [InlineKeyboardButton(f"{math.ceil(int(offset) / int(MAX_BTN)) + 1} / {math.ceil(total / int(MAX_BTN))}", callback_data="pages"),
             InlineKeyboardButton("ɴᴇxᴛ ⪼", callback_data=f"next_{req}_{key}_{n_offset}")])
    else:
        btn.append(
            [
                InlineKeyboardButton("⪻ ʙᴀᴄᴋ", callback_data=f"next_{req}_{key}_{off_set}"),
                InlineKeyboardButton(f"{math.ceil(int(offset) / int(MAX_BTN)) + 1} / {math.ceil(total / int(MAX_BTN))}", callback_data="pages"),
                InlineKeyboardButton("ɴᴇxᴛ ⪼", callback_data=f"next_{req}_{key}_{n_offset}")
            ],
        )
    if settings["link"]:
        links = ""
        for file_num, file in enumerate(files, start=offset+1):
            links += f"""<b>\n\n{file_num}. <a href=https://t.me/{temp.U_NAME}?start=file_{query.message.chat.id}_{file.file_id}>[{get_size(file.file_size)}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file.file_name.split()))}</a></b>"""
        await query.message.edit_text(cap + links + del_msg, disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btn))
        return        
    try:
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(btn)
        )
    except MessageNotModified:
        pass
    await query.answer()
    
@Client.on_callback_query(filters.regex(r"^languages"))
async def languages_cb_handler(client: Client, query: CallbackQuery):
    _, key, req, offset = query.data.split("#")
    if int(req) != query.from_user.id:
        return await query.answer(script.ALRT_TXT, show_alert=True)
    btn = [[
        InlineKeyboardButton(text=lang.title(), callback_data=f"lang_search#{lang}#{key}#{offset}#{req}"),
    ]
        for lang in LANGUAGES
    ]
    btn.append([InlineKeyboardButton(text="⪻ ʙᴀᴄᴋ ᴛᴏ ᴍᴀɪɴ ᴘᴀɢᴇ", callback_data=f"next_{req}_{key}_{offset}")])
    d=await query.message.edit_text("<b>ɪɴ ᴡʜɪᴄʜ ʟᴀɴɢᴜᴀɢᴇ ʏᴏᴜ ᴡᴀɴᴛ, ᴄʜᴏᴏsᴇ ʜᴇʀᴇ 👇 ᴛᴇᴀᴍ: @KR_Picture</b>", reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True)
    await asyncio.sleep(600)
    await d.delete()

@Client.on_callback_query(filters.regex(r"^lang_search"))
async def lang_search(client: Client, query: CallbackQuery):
    _, lang, key, offset, req = query.data.split("#")
    if int(req) != query.from_user.id:
        return await query.answer(script.ALRT_TXT, show_alert=True)	
    offset = int(offset)
    search = BUTTONS.get(key)
    cap = CAP.get(key)
    if not search:
        await query.answer(script.OLD_ALRT_TXT.format(query.from_user.first_name),show_alert=True)
        return 
    search = search.replace("_", " ")
    files, n_offset, total_results = await get_search_results(search, lang=lang)
    if not files:
        await query.answer(f"sᴏʀʀʏ '{lang.title()}' ʟᴀɴɢᴜᴀɢᴇ ꜰɪʟᴇs ɴᴏᴛ ꜰᴏᴜɴᴅ 😕", show_alert=1)
        return
    temp.FILES_ID[key] = files
    reqnxt = query.from_user.id if query.from_user else 0
    settings = await get_settings(query.message.chat.id)
    group_id = query.message.chat.id
    del_msg = f"\n\n<b>⚠️ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ <code>{get_readable_time(DELETE_TIME)}</code> ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs Tᴇᴀᴍ: @KR_Picture</b>" if settings["auto_delete"] else ''
    links = ""
    if settings["link"]:
        btn = []
        for file_num, file in enumerate(files, start=1):
            links += f"""<b>\n\n{file_num}. <a href=https://t.me/{temp.U_NAME}?start=file_{query.message.chat.id}_{file.file_id}>[{get_size(file.file_size)}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file.file_name.split()))}</a></b>"""
    else:
        btn = [[
                InlineKeyboardButton(text=f"🔗 {get_size(file.file_size)}≽ {get_name(file.file_name)}", callback_data=f'files#{reqnxt}#{file.file_id}'),]
                   for file in files
              ]
    if not settings["is_verify"]:
        btn.insert(0,[
            InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ ♻️", url=await get_shortlink(f'https://t.me/{temp.U_NAME}?start=allfiles_{query.message.chat.id}_{key}', group_id)),
            InlineKeyboardButton("🥇ʙᴜʏ🥇", url=f"https://t.me/{temp.U_NAME}?start=buy_premium")
        ])
    else:
        btn.insert(0,[
            InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ ♻️", callback_data=f"send_all#{key}"),
            InlineKeyboardButton("🥇ʙᴜʏ🥇", url=f"https://t.me/{temp.U_NAME}?start=buy_premium")
        ])
    if n_offset != "":
        btn.append(
            [InlineKeyboardButton(text=f"1/{math.ceil(int(total_results) / MAX_BTN)}", callback_data="buttons"),
             InlineKeyboardButton(text="ɴᴇxᴛ »", callback_data=f"lang_next#{req}#{key}#{lang}#{n_offset}#{offset}")]
        )
    btn.append([InlineKeyboardButton(text="⪻ ʙᴀᴄᴋ ᴛᴏ ᴍᴀɪɴ ᴘᴀɢᴇ", callback_data=f"next_{req}_{key}_{offset}")])
    await query.message.edit_text(cap + links + del_msg, disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btn))

@Client.on_callback_query(filters.regex(r"^lang_next"))
async def lang_next_page(bot, query):
    ident, req, key, lang, l_offset, offset = query.data.split("#")
    if int(req) != query.from_user.id:
        return await query.answer(script.ALRT_TXT, show_alert=True)	
    try:
        l_offset = int(l_offset)
    except:
        l_offset = 0
    search = BUTTONS.get(key)
    cap = CAP.get(key)
    grp_id = query.message.chat.id
    settings = await get_settings(query.message.chat.id)
    del_msg = f"\n\n<b>⚠️ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ <code>{get_readable_time(DELETE_TIME)}</code> ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs Tᴇᴀᴍ: @KR_Picture</b>" if settings["auto_delete"] else ''
    if not search:
        await query.answer(f"sᴏʀʀʏ '{lang.title()}' ʟᴀɴɢᴜᴀɢᴇ ꜰɪʟᴇs ɴᴏᴛ ꜰᴏᴜɴᴅ 😕", show_alert=1)
        return
    files, n_offset, total = await get_search_results(search, offset=l_offset, lang=lang)
    if not files:
        return
    temp.FILES_ID[key] = files
    try:
        n_offset = int(n_offset)
    except:
        n_offset = 0
    links = ""
    if settings['link']:
        btn = []
        for file_num, file in enumerate(files, start=l_offset+1):
            links += f"""<b>\n\n{file_num}. <a href=https://t.me/{temp.U_NAME}?start=file_{query.message.chat.id}_{file.file_id}>[{get_size(file.file_size)}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file.file_name.split()))}</a></b>"""
    else:
        btn = [[
            InlineKeyboardButton(text=f"🔗 {get_size(file.file_size)}≽ {get_name(file.file_name)}", callback_data=f'file#{file.file_id}')
        ]
            for file in files
        ]
    if not settings['is_verify']:
        btn.insert(0,[
            InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ ♻️", url=await get_shortlink(f'https://t.me/{temp.U_NAME}?start=allfiles_{query.message.chat.id}_{key}', grp_id)),
            InlineKeyboardButton("🥇ʙᴜʏ🥇", url=f"https://t.me/{temp.U_NAME}?start=buy_premium")
        ])
    else:
        btn.insert(0,[
            InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ ♻️", callback_data=f"send_all#{key}"),
            InlineKeyboardButton("🥇ʙᴜʏ🥇", url=f"https://t.me/{temp.U_NAME}?start=buy_premium")
        ])
    if 0 < l_offset <= MAX_BTN:
        b_offset = 0
    elif l_offset == 0:
        b_offset = None
    else:
        b_offset = l_offset - MAX_BTN
    if n_offset == 0:
        btn.append(
            [InlineKeyboardButton("« ʙᴀᴄᴋ", callback_data=f"lang_next#{req}#{key}#{lang}#{b_offset}#{offset}"),
             InlineKeyboardButton(f"{math.ceil(int(l_offset) / MAX_BTN) + 1}/{math.ceil(total / MAX_BTN)}", callback_data="buttons")]
        )
    elif b_offset is None:
        btn.append(
            [InlineKeyboardButton(f"{math.ceil(int(l_offset) / MAX_BTN) + 1}/{math.ceil(total / MAX_BTN)}", callback_data="buttons"),
             InlineKeyboardButton("ɴᴇxᴛ »", callback_data=f"lang_next#{req}#{key}#{lang}#{n_offset}#{offset}")]
        )
    else:
        btn.append(
            [InlineKeyboardButton("« ʙᴀᴄᴋ", callback_data=f"lang_next#{req}#{key}#{lang}#{b_offset}#{offset}"),
             InlineKeyboardButton(f"{math.ceil(int(l_offset) / MAX_BTN) + 1}/{math.ceil(total / MAX_BTN)}", callback_data="buttons"),
             InlineKeyboardButton("ɴᴇxᴛ »", callback_data=f"lang_next#{req}#{key}#{lang}#{n_offset}#{offset}")]
        )
    btn.append([InlineKeyboardButton(text="⪻ ʙᴀᴄᴋ ᴛᴏ ᴍᴀɪɴ ᴘᴀɢᴇ", callback_data=f"next_{req}_{key}_{offset}")])
    await query.message.edit_text(cap + links + del_msg, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML)

@Client.on_callback_query(filters.regex(r"^spol"))
async def advantage_spoll_choker(bot, query):
    _, id, user = query.data.split('#')
    if int(user) != 0 and query.from_user.id != int(user):
        return await query.answer(script.ALRT_TXT, show_alert=True)
    movie = await get_poster(id, id=True)
    search = movie.get('title')
    await query.answer('ᴄʜᴇᴄᴋɪɴɢ ɪɴ ᴍʏ ᴅᴀᴛᴀʙᴀꜱᴇ 🌚')
    files, offset, total_results = await get_search_results(search)
    if files:
        k = (search, files, offset, total_results)
        await auto_filter(bot, query, k)
    else:
        k = await query.message.edit(script.NO_RESULT_TXT)
        await asyncio.sleep(60)
        await k.delete()
        try:
            await query.message.reply_to_message.delete()
        except:
            pass

@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    if query.data == "close_data":
        try:
            user = query.message.reply_to_message.from_user.id
        except:
            user = query.from_user.id
        if int(user) != 0 and query.from_user.id != int(user):
            return await query.answer(script.ALRT_TXT, show_alert=True)
        await query.answer("ᴛʜᴀɴᴋs ꜰᴏʀ ᴄʟᴏsᴇ 🙈 ᴛᴇᴀᴍ: @KR_Picture")
        await query.message.delete()
        try:
            await query.message.reply_to_message.delete()
        except:
            pass

    elif query.data.startswith("checksub"):
        ident, file_id = query.data.split("#")
        settings = await get_settings(query.message.chat.id)
        if AUTH_CHANNEL and not await is_req_subscribed(client, query):
            await query.answer("ɪ ʟɪᴋᴇ ʏᴏᴜʀ sᴍᴀʀᴛɴᴇss ʙᴜᴛ ᴅᴏɴ'ᴛ ʙᴇ ᴏᴠᴇʀsᴍᴀʀᴛ 😒\nꜰɪʀsᴛ ᴊᴏɪɴ ᴏᴜʀ ᴜᴘᴅᴀᴛᴇs ᴄʜᴀɴɴᴇʟ 😒 ᴛᴇᴀᴍ: @KR_Picture", show_alert=True)
            return         
        files_ = await get_file_details(file_id)
        if not files_:
            return await query.answer('ɴᴏ sᴜᴄʜ ꜰɪʟᴇ ᴇxɪsᴛs 🚫')
        files = files_[0]
        CAPTION = settings['caption']
        f_caption = CAPTION.format(
            file_name = files.file_name,
            file_size = get_size(files.file_size),
            file_caption = files.caption
        )
        await client.send_cached_media(
            chat_id=query.from_user.id,
            file_id=file_id,
            caption=f_caption,
            protect_content=settings['file_secure'],
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton('❌ ᴄʟᴏsᴇ ❌', callback_data='close_data')
                    ]
                ]
            )
        )

    elif query.data.startswith("stream"):
        user_id = query.from_user.id
        if not await db.has_premium_access(user_id):
            d=await query.message.reply("<b>💔 ᴛʜɪꜱ ꜰᴇᴀᴛᴜʀᴇ ɪꜱ ᴏɴʟʏ ꜰᴏʀ ʙᴏᴛ ᴘʀᴇᴍɪᴜᴍ ᴜꜱᴇʀꜱ.\n\nɪꜰ ʏᴏᴜ ᴡᴀɴᴛ ʙᴏᴛ ꜱᴜʙꜱᴄʀɪᴘᴛɪᴏɴ ᴛʜᴇɴ ꜱᴇɴᴅ /plan</b>")
            await asyncio.sleep(120)
            await d.delete()
            return
        file_id = query.data.split('#', 1)[1]
        NOBITA = await client.send_cached_media(
            chat_id=BIN_CHANNEL,
            file_id=file_id)
        online = f"https://{URL}/watch/{NOBITA.id}?hash={get_hash(NOBITA)}"
        download = f"https://{URL}/{NOBITA.id}?hash={get_hash(NOBITA)}"
        btn= [[
            InlineKeyboardButton("ᴡᴀᴛᴄʜ ᴏɴʟɪɴᴇ", url=online),
            InlineKeyboardButton("ꜰᴀsᴛ ᴅᴏᴡɴʟᴏᴀᴅ", url=download)
        ],[
            InlineKeyboardButton('🧿 Wᴀᴛᴄʜ ᴏɴ ᴛᴇʟᴇɢʀᴀᴍ 🖥', web_app=WebAppInfo(url=online))
        ]]
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(btn)
        )

    elif query.data == "buttons":
        await query.answer("ɴᴏ ᴍᴏʀᴇ ᴘᴀɢᴇs 😊", show_alert=True)

    elif query.data == "pages":
        await query.answer("ᴛʜɪs ɪs ᴘᴀɢᴇs ʙᴜᴛᴛᴏɴ 😅")

    elif query.data.startswith("lang_art"):
        _, lang = query.data.split("#")
        await query.answer(f"ʏᴏᴜ sᴇʟᴇᴄᴛᴇᴅ {lang.title()} ʟᴀɴɢᴜᴀɢᴇ ⚡️", show_alert=True)
  
    elif query.data == "start":
        buttons = [[
            InlineKeyboardButton('• Bᴀᴄᴋᴜᴘ Cʜᴀɴɴᴇʟ •', url=f'https://t.me/sandalwood_kannada_moviesz')
            ],[
                InlineKeyboardButton('• Mᴏᴠɪᴇ Gʀᴏᴜᴘ •', url=f'https://t.me/+x6OfRDdUPrUwZTZl'),
                InlineKeyboardButton('• Mᴀɪɴ Cʜᴀɴɴᴇʟ •', url=f'https://t.me/+fDkIGNmk5BU5ODVl')
            ],[
                InlineKeyboardButton('• Hᴇʟᴘ •', callback_data='buy_premium')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.START_TXT.format(query.from_user.mention, get_status(), query.from_user.id),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )      
    elif query.data == "features":
        buttons = [[
            InlineKeyboardButton('📸 ɪᴍᴀɢᴇ', callback_data='uploader'),
            InlineKeyboardButton('🆎️ ꜰᴏɴᴛ', callback_data='font')    
        ], [ 
            InlineKeyboardButton('⋞ ʙᴀᴄᴋ', callback_data='start')
        ]] 
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(                     
            text=script.HELP_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )

    elif query.data.startswith("techifybots"):
        ident, keyword = query.data.split("#")
        await query.message.edit_text(f"<b>Fᴇᴛᴄʜɪɴɢ Fɪʟᴇs ғᴏʀ ʏᴏᴜʀ ᴏ̨ᴜᴇʀʏ {keyword} ᴏɴ DB... Pʟᴇᴀsᴇ ᴡᴀɪᴛ...</b>")
        files, total = await get_bad_files(keyword)
        await query.message.edit_text(f"<b>Fᴏᴜɴᴅ {total} Fɪʟᴇs ғᴏʀ ʏᴏᴜʀ ᴏ̨ᴜᴇʀʏ {keyword} !\n\nFɪʟᴇ ᴅᴇʟᴇᴛɪᴏɴ ᴘʀᴏᴄᴇss ᴡɪʟʟ sᴛᴀʀᴛ ɪɴ 5 sᴇᴄᴏɴᴅs!</b>")
        await asyncio.sleep(5)
        deleted = 0
        async with lock:
            try:
                for file in files:
                    file_ids = file.file_id
                    file_name = file.file_name
                    result = await Media.collection.delete_one({
                        '_id': file_ids,
                    })
                    if result.deleted_count:
                        logger.info(f'Fɪʟᴇ Fᴏᴜɴᴅ ғᴏʀ ʏᴏᴜʀ ᴏ̨ᴜᴇʀʏ {keyword}! Sᴜᴄᴄᴇssғᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ {file_name} ғʀᴏᴍ ᴅᴀᴛᴀʙᴀsᴇ.')
                        deleted += 1
                        if deleted % 20 == 0:
                            await query.message.edit_text(f"<b>Pʀᴏᴄᴇss sᴛᴀʀᴛᴇᴅ ғᴏʀ ᴅᴇʟᴇᴛɪɴɢ ғɪʟᴇs ғʀᴏᴍ DB. Sᴜᴄᴄᴇssғᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ {str(deleted)} ғɪʟᴇs ғʀᴏᴍ DB ғᴏʀ ʏᴏᴜʀ ᴏ̨ᴜᴇʀʏ {keyword} !\n\nPʟᴇᴀsᴇ ᴡᴀɪᴛ...</b>")
            except Exception as e:
                logger.exception(e)
                await query.message.edit_text(f'Eʀʀᴏʀ: {e}')
            else:
                await query.message.edit_text(f"<b>Pʀᴏᴄᴇss Cᴏᴍᴘʟᴇᴛᴇᴅ ғᴏʀ ғɪʟᴇ ᴅᴇʟᴇᴛɪᴏɴ !\n\nSᴜᴄᴄᴇssғᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ {str(deleted)} ғɪʟᴇs ғʀᴏᴍ DB ғᴏʀ ʏᴏᴜʀ ᴏ̨ᴜᴇʀʏ {keyword}.</b>")

    elif query.data == "earn":
        buttons = [[
            InlineKeyboardButton('♻️ ᴄᴜꜱᴛᴏᴍɪᴢᴇ ʏᴏᴜʀ ɢʀᴏᴜᴘ ♻️', callback_data='custom')    
        ], [ 
            InlineKeyboardButton('⋞ ʙᴀᴄᴋ', callback_data='start'),
            InlineKeyboardButton('sᴜᴘᴘᴏʀᴛ', url=USERNAME)
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
             text=script.EARN_TEXT.format(temp.B_LINK),
             reply_markup=reply_markup,
             disable_web_page_preview=True,
             parse_mode=enums.ParseMode.HTML
         )
    elif query.data == "uploader":
        buttons = [[
            InlineKeyboardButton('⋞ ʙᴀᴄᴋ', callback_data='features')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)  
        await query.message.edit_text(
            text=script.IMGUPL,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "font":
        buttons = [[
            InlineKeyboardButton('⋞ ʙᴀᴄᴋ', callback_data='features')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons) 
        await query.message.edit_text(
            text=script.FONT_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "custom":
        buttons = [[
            InlineKeyboardButton('⋞ ʙᴀᴄᴋ', callback_data='earn')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons) 
        await query.message.edit_text(
            text=script.CUSTOM_TEXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
    elif query.data == "buy_premium":
        btn = [[
            InlineKeyboardButton('📸 sᴇɴᴅ sᴄʀᴇᴇɴsʜᴏᴛ 📸', url=USERNAME)
        ],[
            InlineKeyboardButton('🗑 ᴄʟᴏsᴇ 🗑', callback_data='close_data')
        ]]
        reply_markup = InlineKeyboardMarkup(btn)
        await query.message.reply_photo(
            photo=(QR_CODE),
            caption=script.PREMIUM_TEXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )

    elif query.data.startswith("setgs"):
        ident, set_type, status, grp_id = query.data.split("#")
        userid = query.from_user.id if query.from_user else None
        if not await is_check_admin(client, int(grp_id), userid):
            await query.answer(script.ALRT_TXT, show_alert=True)
            return
        if status == "True":
            await save_group_settings(int(grp_id), set_type, False)
        else:
            await save_group_settings(int(grp_id), set_type, True)
        settings = await get_settings(int(grp_id))      
        if settings is not None:
            buttons = [[
                InlineKeyboardButton('ᴀᴜᴛᴏ ꜰɪʟᴛᴇʀ', callback_data=f'setgs#auto_filter#{settings["auto_filter"]}#{grp_id}'),
                InlineKeyboardButton('ᴏɴ ✔️' if settings["auto_filter"] else 'ᴏꜰꜰ ✗', callback_data=f'setgs#auto_filter#{settings["auto_filter"]}#{grp_id}')
            ],[
                InlineKeyboardButton('ꜰɪʟᴇ sᴇᴄᴜʀᴇ', callback_data=f'setgs#file_secure#{settings["file_secure"]}#{grp_id}'),
                InlineKeyboardButton('ᴏɴ ✔️' if settings["file_secure"] else 'ᴏꜰꜰ ✗', callback_data=f'setgs#file_secure#{settings["file_secure"]}#{grp_id}')
            ],[
                InlineKeyboardButton('ɪᴍᴅʙ', callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}'),
                InlineKeyboardButton('ᴏɴ ✔️' if settings["imdb"] else 'ᴏꜰꜰ ✗', callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}')
            ],[
                InlineKeyboardButton('sᴘᴇʟʟ ᴄʜᴇᴄᴋ', callback_data=f'setgs#spell_check#{settings["spell_check"]}#{grp_id}'),
                InlineKeyboardButton('ᴏɴ ✔️' if settings["spell_check"] else 'ᴏꜰꜰ ✗', callback_data=f'setgs#spell_check#{settings["spell_check"]}#{grp_id}')
            ],[
                InlineKeyboardButton('ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ', callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{grp_id}'),
                InlineKeyboardButton(f'{get_readable_time(DELETE_TIME)}' if settings["auto_delete"] else 'ᴏꜰꜰ ✗', callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{grp_id}')
            ],[
                InlineKeyboardButton('ʀᴇsᴜʟᴛ ᴍᴏᴅᴇ', callback_data=f'setgs#link#{settings["link"]}#{str(grp_id)}'),
                InlineKeyboardButton('ʟɪɴᴋ' if settings["link"] else 'ʙᴜᴛᴛᴏɴ', callback_data=f'setgs#link#{settings["link"]}#{str(grp_id)}')
            ],[
                InlineKeyboardButton('ꜰɪʟᴇꜱ ᴍᴏᴅᴇ', callback_data=f'setgs#is_verify#{settings.get("is_verify", IS_VERIFY)}#{grp_id}'),
                InlineKeyboardButton('ᴠᴇʀɪꜰʏ' if settings.get("is_verify", IS_VERIFY) else 'ꜱʜᴏʀᴛʟɪɴᴋ', callback_data=f'setgs#is_verify#{settings.get("is_verify", IS_VERIFY)}#{grp_id}')
            ],[
                InlineKeyboardButton('☕️ ᴄʟᴏsᴇ ☕️', callback_data='close_data')
            ]]
            reply_markup = InlineKeyboardMarkup(buttons)
            d = await query.message.edit_reply_markup(reply_markup)
            await asyncio.sleep(300)
            await d.delete()
        else:
            await query.message.edit_text("<b>ꜱᴏᴍᴇᴛʜɪɴɢ ᴡᴇɴᴛ ᴡʀᴏɴɢ</b>")

    elif query.data.startswith("send_all"):
        ident, key = query.data.split("#")
        user = query.message.reply_to_message.from_user.id
        if int(user) != 0 and query.from_user.id != int(user):
            return await query.answer(f"Hello {query.from_user.first_name},\nDon't Click Other Results!", show_alert=True)
        files = temp.FILES_ID.get(key)
        if not files:
            await query.answer(script.OLD_ALRT_TXT.format(query.from_user.first_name),show_alert=True)
            return        
        await query.answer(url=f"https://t.me/{temp.U_NAME}?start=allfiles_{query.message.chat.id}_{key}")

async def auto_filter(client, msg, spoll=False):
    if not spoll:
        message = msg
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
        search, files, offset, total_results = spoll
    grp_id = message.chat.id
    req = message.from_user.id if message.from_user else 0
    key = f"{message.chat.id}-{message.id}"
    temp.FILES_ID[f"{message.chat.id}-{message.id}"] = files
    pre = 'filep' if settings['file_secure'] else 'file'
    temp.CHAT[message.from_user.id] = message.chat.id
    settings = await get_settings(message.chat.id)
    del_msg = f"\n\n<b>⚠️ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ <code>{get_readable_time(DELETE_TIME)}</code> ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs Tᴇᴀᴍ: @KR_Picture</b>" if settings["auto_delete"] else ''
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
    del_msg = f"\n\n<b>⚠️ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ <code>{get_readable_time(DELETE_TIME)}</code> ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs Tᴇᴀᴍ: @KR_Picture</b>" if settings["auto_delete"] else ''
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
            buttons = [[InlineKeyboardButton('✧ ᴛᴀᴋᴇ ꜰɪʟᴇ ꜰʀᴏᴍ ʜᴇʀᴇ ✧', url="https://telegram.me/+x6OfRDdUPrUwZTZl")]]
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
