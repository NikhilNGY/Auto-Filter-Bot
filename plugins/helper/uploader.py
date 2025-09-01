import os
import asyncio
import aiohttp
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

UPLOAD_URL = "https://envs.sh"


async def upload_image_aiohttp(image_path: str) -> str | None:
    """Upload file asynchronously using aiohttp"""
    try:
        async with aiohttp.ClientSession() as session:
            with open(image_path, "rb") as f:
                data = {"file": f}
                async with session.post(UPLOAD_URL, data=data) as resp:
                    if resp.status == 200:
                        return (await resp.text()).strip()
                    return None
    except Exception as e:
        print(f"Upload error: {e}")
        return None


@Client.on_message(filters.command("upload") & filters.private)
async def upload_command(client, message):
    replied = message.reply_to_message
    if not replied:
        await message.reply_text("⚠️ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴍᴇᴅɪᴀ ᴜɴᴅᴇʀ 𝟻 ᴍʙ")
        return

    # Properly fetch file size from media
    file_size = None
    if replied.document:
        file_size = replied.document.file_size
    elif replied.photo:
        file_size = replied.photo.file_size
    elif replied.video:
        file_size = replied.video.file_size
    elif replied.audio:
        file_size = replied.audio.file_size
    elif replied.voice:
        file_size = replied.voice.file_size

    if file_size and file_size > 5 * 1024 * 1024:
        await message.reply_text("⚠️ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴍᴇᴅɪᴀ ᴜɴᴅᴇʀ 𝟻 ᴍʙ")
        return

    uploader = await replied.download()
    uploading_message = await message.reply_text("<code>ᴜᴘʟᴏᴀᴅɪɴɢ...</code>")

    url = await upload_image_aiohttp(uploader)
    if not url:
        await uploading_message.edit_text("❌ Upload failed. Try again later.")
        return

    try:
        os.remove(uploader)
    except Exception as e:
        print(f"Error removing file: {e}")

    await uploading_message.delete()

    techifybots = await message.reply_photo(
        photo=url,
        caption=(
            f"<b>ʏᴏᴜʀ ᴄʟᴏᴜᴅ ʟɪɴᴋ ᴄᴏᴍᴘʟᴇᴛᴇᴅ 👇</b>\n\n"
            f"𝑳𝒊𝒏𝒌 :-\n\n<code>{url}</code>\n\n"
            f"<b>ᴘᴏᴡᴇʀᴇᴅ ʙʏ - @KR_PICTURE</b>"
        ),
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("• ᴏᴘᴇɴ ʟɪɴᴋ •", url=url),
                InlineKeyboardButton("• sʜᴀʀᴇ ʟɪɴᴋ •", url=f"https://t.me/share/url?url={url}")
            ],
            [
                InlineKeyboardButton("❌   ᴄʟᴏsᴇ   ❌", callback_data="close_data")
            ]
        ])
    )

    await asyncio.sleep(120)
    await techifybots.delete()
