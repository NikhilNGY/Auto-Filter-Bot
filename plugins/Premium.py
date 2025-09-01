import pytz
import datetime
import asyncio
from info import ADMINS, USERNAME, LOG_CHANNEL, QR_CODE
from Script import script 
from utils import get_seconds
from database.users_chats_db import db 
from pyrogram import Client, filters 
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors.exceptions.bad_request_400 import MessageTooLong


# ───────────── Helper ───────────── #
async def get_target_user(client, message, args_index=1):
    """
    Returns a pyrogram.User object based on:
    - reply
    - username (@username)
    - user ID (integer)
    """
    if message.reply_to_message:  # Case 1: reply
        return await client.get_users(message.reply_to_message.from_user.id)

    if len(message.command) > args_index:  # Case 2: username or ID in args
        identifier = message.command[args_index]
        try:
            return await client.get_users(identifier)
        except Exception as e:
            await message.reply_text(f"⚠️ Could not fetch user: {e}")
            return None

    await message.reply_text("⚠️ Please reply to a user or provide a user ID/username.")
    return None


# ───────────── ADD PREMIUM ───────────── #
@Client.on_message(filters.command("addpremium") & filters.user(ADMINS) & (filters.group | filters.private))
async def add_premium(client, message):
    try:
        if len(message.command) < 2 and not message.reply_to_message:
            return await message.reply_text(
                "Usage:\n/addpremium <user_id or @username> <time> [custom_message]\n"
                "Or reply to a user with /addpremium <time> [custom_message]"
            )

        args_index = 1 if not message.reply_to_message else 0
        user = await get_target_user(client, message, args_index=args_index)
        if not user:
            return

        time = message.command[args_index + 1] if len(message.command) > args_index + 1 else None
        if not time:
            return await message.reply_text("⚠️ Please provide duration. Example: `/addpremium @username 1day`")

        custom_message = " ".join(message.command[args_index + 2:]) if len(message.command) > args_index + 2 else "𝑻𝒉𝒂𝒏𝒌𝒔 𝑭𝒐𝒓 𝑻𝒂𝒌𝒊𝒏𝒈 𝑺𝒖𝒃𝒔𝒄𝒓𝒊𝒑𝒕𝒊𝒐𝒏"

        time_zone = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))
        current_time = time_zone.strftime("%d-%m-%Y : %I:%M:%S %p")
        seconds = await get_seconds(time)

        if seconds > 0:
            expiry_time = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
            user_data = {"id": user.id, "expiry_time": expiry_time}
            await db.update_user(user_data)
            data = await db.get_user(user.id)
            expiry = data.get("expiry_time")
            expiry_str_in_ist = expiry.astimezone(pytz.timezone("Asia/Kolkata")).strftime("%d-%m-%Y  :  %I:%M:%S %p")

            await message.reply_text(
                f"Premium access added ✅\n\n"
                f"👤 User: {user.mention}\n"
                f"🪙 User ID: <code>{user.id}</code>\n"
                f"⏰ Access: {time}\n"
                f"🎩 Joining : {current_time}\n"
                f"⌛️ Expiry: {expiry_str_in_ist}"
            )

            await client.send_message(
                chat_id=user.id,
                text=f"<b>{user.mention},\n\nᴘʀᴇᴍɪᴜᴍ ᴀᴅᴅᴇᴅ ✅\n\nᴘʀᴇᴍɪᴜᴍ - {time}\nᴊᴏɪɴɪɴɢ - {current_time}\nᴇxᴘɪʀᴇs - {expiry_str_in_ist}</b>\n\n{custom_message}"
            )

            await client.send_message(
                LOG_CHANNEL,
                text=f"#Added_Premium\n\n👤 User - {user.mention}\n🪙 Id - <code>{user.id}</code>\n⏰ Premium - {time}\n🎩 Joining - {current_time}\n⌛️ Expiry - {expiry_str_in_ist}\n{custom_message}"
            )
        else:
            await message.reply_text("⚠️ Invalid time format. Example: `/addpremium 1030335104 1day`")

    except Exception as e:
        await message.reply_text(f"Error: {e}")


# ───────────── REMOVE PREMIUM ───────────── #
@Client.on_message(filters.command("removepremium") & filters.user(ADMINS) & (filters.group | filters.private))
async def remove_premium(client, message):
    user = await get_target_user(client, message)
    if not user:
        return
    if await db.remove_premium_access(user.id):
        await message.reply_text("<b>sᴜᴄᴄᴇssꜰᴜʟʟʏ ʀᴇᴍᴏᴠᴇᴅ ✅</b>")
        await client.send_message(
            chat_id=user.id,
            text=f"<b>ʜʏ {user.mention},\n\n⚠️ ʏᴏᴜʀ ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇss ʜᴀs ʙᴇᴇɴ ʀᴇᴍᴏᴠᴇᴅ 🚫</b>"
        )
    else:
        await message.reply_text("<b>👀 ᴜɴᴀʙʟᴇ ᴛᴏ ʀᴇᴍᴏᴠᴇ, ᴀʀᴇ ʏᴏᴜ sᴜʀᴇ ɪᴛ ᴡᴀs ᴀ ᴘʀᴇᴍɪᴜᴍ ᴜsᴇʀ??</b>")


# ───────────── CHECK PLAN ───────────── #
@Client.on_message(filters.command("checkplan") & filters.user(ADMINS) & (filters.group | filters.private))
async def check_plan(client, message):
    user = await get_target_user(client, message)
    if not user:
        return
    user_data = await db.get_user(user.id)

    if user_data and user_data.get("expiry_time"):
        expiry = user_data.get("expiry_time")
        expiry_ist = expiry.astimezone(pytz.timezone("Asia/Kolkata"))
        expiry_str_in_ist = expiry.astimezone(pytz.timezone("Asia/Kolkata")).strftime("%d-%m-%Y %I:%M:%S %p")
        current_time = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))
        time_left = expiry_ist - current_time
        days = time_left.days
        hours, remainder = divmod(time_left.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        time_left_str = f"{days} days, {hours} hours, {minutes} minutes"
        response = (
            f"User ID: {user.id}\n"
            f"Name: {user.mention}\n"
            f"Expiry Date: {expiry_str_in_ist}\n"
            f"Time Left: {time_left_str}"
        )
    else:
        response = "User does not have premium..."
    await message.reply_text(response)


# ───────────── MY PLAN (users) ───────────── #
@Client.on_message(filters.command("myplan") & (filters.group | filters.private))
async def myplan(client, message):
    user = message.from_user.mention 
    user_id = message.from_user.id
    data = await db.get_user(user_id)
    if data and data.get("expiry_time"):
        expiry = data.get("expiry_time") 
        expiry_ist = expiry.astimezone(pytz.timezone("Asia/Kolkata"))
        expiry_str_in_ist = expiry_ist.strftime("%d-%m-%Y  ⏰: %I:%M:%S %p")            
        current_time = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))
        time_left = expiry_ist - current_time
        days = time_left.days
        hours, remainder = divmod(time_left.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        time_left_str = f"{days} days, {hours} hours, {minutes} minutes"
        await message.reply_text(f"#Premium_Info:\n\n👤 User: {user}\n\n🪙 User Id: <code>{user_id}</code>\n\n⏰ Time Left: {time_left_str}\n\n⌛️ Expiry: {expiry_str_in_ist}.")   
    else:
        await message.reply_text(f"<b>{user},\n\nʏᴏᴜ ᴅᴏ ɴᴏᴛ ʜᴀᴠᴇ ᴀɴʏ ᴀᴄᴛɪᴠᴇ ᴘʀᴇᴍɪᴜᴍ ᴘʟᴀɴs, ɪꜰ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴛᴀᴋᴇ ᴘʀᴇᴍɪᴜᴍ ᴛʜᴇɴ ᴄʜᴇᴄᴋ /plan ꜰᴏʀ ᴍᴏʀᴇ ᴅᴇᴛᴀɪʟs...</b>")


# ───────────── PLAN INFO (users) ───────────── #
@Client.on_message(filters.command('plan') & (filters.group | filters.private))
async def plan(client, message):
    user_id = message.from_user.id
    if message.from_user.username:
        user_info = f"@{message.from_user.username}"
    else:
        user_info = f"{message.from_user.mention}"
    log_message = f"#Plan\n\n<b>🚫 ᴛʜɪs ᴜsᴇʀ ᴛʀʏ ᴛᴏ ᴄʜᴇᴄᴋ ᴘʟᴀɴ\n\n- ɪᴅ - `{user_id}`\n- ɴᴀᴍᴇ - {user_info}</b>"
    btn = [[
        InlineKeyboardButton("📸  sᴇɴᴅ sᴄʀᴇᴇɴsʜᴏᴛ  📸", url=USERNAME),
    ],[
        InlineKeyboardButton("🗑  ᴄʟᴏsᴇ  🗑", callback_data="close_data")
    ]]
    await client.send_message(LOG_CHANNEL, log_message)
    r=await message.reply_photo(
        photo=(QR_CODE),
        caption=script.PREMIUM_TEXT, 
        reply_markup=InlineKeyboardMarkup(btn))
    await asyncio.sleep(120)
    await r.delete()


# ───────────── PREMIUM USERS LIST ───────────── #
@Client.on_message(filters.command("premiumuser") & filters.user(ADMINS) & (filters.group | filters.private))
async def premium_user(client, message):
    aa = await message.reply_text("Fetching ...")  
    users = await db.get_all_users()
    users_list = []
    async for user in users:
        users_list.append(user)    
    user_data = {user['id']: await db.get_user(user['id']) for user in users_list}    
    new_users = []
    for user in users_list:
        user_id = user['id']
        data = user_data.get(user_id)
        expiry = data.get("expiry_time") if data else None        
        if expiry:
            expiry_ist = expiry.astimezone(pytz.timezone("Asia/Kolkata"))
            expiry_str_in_ist = expiry_ist.strftime("%d-%m-%Y %I:%M:%S %p")          
            current_time = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))
            time_left = expiry_ist - current_time
            days, remainder = divmod(time_left.total_seconds(), 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, _ = divmod(remainder, 60)            
            time_left_str = f"{int(days)} days, {int(hours)} hours, {int(minutes)} minutes"            
            user_info = await client.get_users(user_id)
            user_str = (
                f"{len(new_users) + 1}. User ID: {user_id}\n"
                f"Name: {user_info.mention}\n"
                f"Expiry Date: {expiry_str_in_ist}\n"
                f"Time Left: {time_left_str}\n\n"
            )
            new_users.append(user_str)
    new = "Paid Users - \n\n" + "\n".join(new_users)   
    try:
        await aa.edit_text(new)
    except MessageTooLong:
        with open('premiumuser.txt', 'w+') as outfile:
            outfile.write(new)
        await message.reply_document('premiumuser.txt', caption="Paid Users:")
