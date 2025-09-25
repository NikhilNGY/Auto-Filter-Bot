from pyrogram import Client, emoji
from pyrogram.types import (InlineKeyboardButton, InlineKeyboardMarkup,
                            InlineQuery, InlineQueryResultCachedDocument)

from database.ia_filterdb import get_search_results
from info import CACHE_TIME, FILE_CAPTION, SUPPORT_LINK, UPDATES_LINK
from utils import get_size, temp

cache_time = CACHE_TIME


def is_banned(query: InlineQuery):
    return query.from_user and query.from_user.id in temp.BANNED_USERS


@Client.on_inline_query()
async def inline_search(bot, query):
    """Show search results for given inline query"""

    if is_banned(query):
        await query.answer(
            results=[],
            cache_time=0,
            switch_pm_text="You're banned user :(",
            switch_pm_parameter="start",
        )
        return

    results = []
    string = query.query
    offset = int(query.offset or 0)
    files, next_offset, total = await get_search_results(string, offset=offset)

    for file in files:
        reply_markup = get_reply_markup()
        f_caption = FILE_CAPTION.format(
            file_name=file.file_name,
            file_size=get_size(file.file_size),
            caption=file.caption,
        )
        results.append(
            InlineQueryResultCachedDocument(
                title=file.file_name,
                document_file_id=file.file_id,
                caption=f_caption,
                description=f"Size: {get_size(file.file_size)}",
                reply_markup=reply_markup,
            )
        )

    if results:
        switch_pm_text = f"{emoji.FILE_FOLDER} Results - {total}"
        if string:
            switch_pm_text += f" For: {string}"
        await query.answer(
            results=results,
            is_personal=True,
            cache_time=cache_time,
            switch_pm_text=switch_pm_text,
            switch_pm_parameter="start",
            next_offset=str(next_offset),
        )
    else:
        switch_pm_text = f"{emoji.CROSS_MARK} No Results"
        if string:
            switch_pm_text += f" For: {string}"
        await query.answer(
            results=[],
            is_personal=True,
            cache_time=cache_time,
            switch_pm_text=switch_pm_text,
            switch_pm_parameter="start",
        )


def get_reply_markup():
    buttons = [
        [
            InlineKeyboardButton("⚡️ ᴜᴘᴅᴀᴛᴇs ᴄʜᴀɴɴᴇʟ ⚡️", url=UPDATES_LINK),
            InlineKeyboardButton("💡 Support Group 💡", url=SUPPORT_LINK),
        ]
    ]
    return InlineKeyboardMarkup(buttons)
