"""Admin command handlers."""
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from bot.services.database import db
from bot.config import config
from bot.utils.logging import log_admin_command

router = Router()


@router.message(Command("addadmin"))
async def cmd_addadmin(message: Message):
    """Handle /addadmin <user_id> command (Owner only)."""
    user_id = message.from_user.id
    
    # Check if user is owner
    if not config.is_owner(user_id):
        log_admin_command(user_id, "UNAUTHORIZED ADDADMIN ATTEMPT", 0)
        await message.reply(
            "❌ *Error*: Unauthorized action. Only the bot owner can manage administrators.",
            parse_mode="Markdown"
        )
        return
        
    args = message.text.split()
    if len(args) != 2:
        await message.reply(
            "❌ *Usage*: `/addadmin <user_id>`\n"
            "Example: `/addadmin 123456789`",
            parse_mode="Markdown"
        )
        return
        
    try:
        target_id = int(args[1])
    except ValueError:
        await message.reply(
            "❌ *Error*: Invalid user ID. ID must be a number.",
            parse_mode="Markdown"
        )
        return
        
    # Prevent duplicate admins
    db_admins = await db.get_admins()
    if target_id == config.owner_id or target_id in config.admin_ids or target_id in db_admins:
        await message.reply(
            f"⚠ *Warning*: User `{target_id}` is already an administrator.",
            parse_mode="Markdown"
        )
        return
        
    # Add admin
    added = await db.add_admin(target_id)
    if added:
        log_admin_command(user_id, "Added Admin", target_id)
        
        # Send confirmation in channel
        if config.log_channel_id:
            try:
                await message.bot.send_message(
                    config.log_channel_id,
                    f"🛡 *Admin Added*\n\n"
                    f"👑 *Owner:* `{user_id}`\n"
                    f"👤 *New Admin:* `{target_id}`",
                    parse_mode="Markdown"
                )
            except Exception:
                pass

        await message.reply(
            "✅ *↯ 〔 ADMIN ADDED 〕 ↯*\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 *User ID:* `{target_id}` has been successfully promoted to administrator.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━",
            parse_mode="Markdown"
        )
    else:
        await message.reply(
            "❌ *Error*: Failed to add admin.",
            parse_mode="Markdown"
        )


@router.message(Command("removeadmin"))
async def cmd_removeadmin(message: Message):
    """Handle /removeadmin <user_id> command (Owner only)."""
    user_id = message.from_user.id
    
    # Check if user is owner
    if not config.is_owner(user_id):
        log_admin_command(user_id, "UNAUTHORIZED REMOVEADMIN ATTEMPT", 0)
        await message.reply(
            "❌ *Error*: Unauthorized action. Only the bot owner can manage administrators.",
            parse_mode="Markdown"
        )
        return
        
    args = message.text.split()
    if len(args) != 2:
        await message.reply(
            "❌ *Usage*: `/removeadmin <user_id>`\n"
            "Example: `/removeadmin 123456789`",
            parse_mode="Markdown"
        )
        return
        
    try:
        target_id = int(args[1])
    except ValueError:
        await message.reply(
            "❌ *Error*: Invalid user ID. ID must be a number.",
            parse_mode="Markdown"
        )
        return
        
    # Prevent removing owner
    if target_id == config.owner_id:
        await message.reply(
            "❌ *Error*: Cannot remove the owner from administrators.",
            parse_mode="Markdown"
        )
        return
        
    # Check if they are actually a database admin
    db_admins = await db.get_admins()
    if target_id not in db_admins:
        if target_id in config.admin_ids:
            await message.reply(
                f"❌ *Error*: User `{target_id}` is defined as admin in configuration file and cannot be removed dynamically.",
                parse_mode="Markdown"
            )
        else:
            await message.reply(
                f"❌ *Error*: User `{target_id}` is not an administrator.",
                parse_mode="Markdown"
            )
        return
        
    # Remove admin
    removed = await db.remove_admin(target_id)
    if removed:
        log_admin_command(user_id, "Removed Admin", target_id)
        
        # Send confirmation in channel
        if config.log_channel_id:
            try:
                await message.bot.send_message(
                    config.log_channel_id,
                    f"🛡 *Admin Removed*\n\n"
                    f"👑 *Owner:* `{user_id}`\n"
                    f"👤 *Demoted Admin:* `{target_id}`",
                    parse_mode="Markdown"
                )
            except Exception:
                pass

        await message.reply(
            "✅ *↯ 〔 ADMIN REMOVED 〕 ↯*\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 *User ID:* `{target_id}` has been successfully demoted to member.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━",
            parse_mode="Markdown"
        )
    else:
        await message.reply(
            "❌ *Error*: Failed to remove admin.",
            parse_mode="Markdown"
        )


@router.message(Command("admins"))
async def cmd_admins(message: Message):
    """Handle /admins command (Owner only)."""
    user_id = message.from_user.id
    
    # Check if user is owner
    if not config.is_owner(user_id):
        log_admin_command(user_id, "UNAUTHORIZED ADMINS VIEW ATTEMPT", 0)
        await message.reply(
            "❌ *Error*: Unauthorized action. Only the bot owner can view the administrators list.",
            parse_mode="Markdown"
        )
        return
        
    db_admins = await db.get_admins()
    
    admin_list = ""
    # Hardcoded config admins
    for a_id in config.admin_ids:
        if a_id != config.owner_id:
            admin_list += f" ├ `{a_id}` (Config)\n"
            
    # Database dynamic admins
    for idx, a_id in enumerate(db_admins):
        is_last = (idx == len(db_admins) - 1)
        prefix = " └" if is_last else " ├"
        admin_list += f"{prefix} `{a_id}` (Database)\n"
        
    if not admin_list:
        admin_list = " └ *No additional administrators*\n"
        
    admins_text = (
        "🛡 *↯ 〔 ADMINISTRATORS LIST 〕 ↯*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👑 *Owner:*\n"
        f" └ `{config.owner_id}`\n\n"
        f"🛡 *Admins:*\n"
        f"{admin_list}"
        "━━━━━━━━━━━━━━━━━━━━━"
    )
    
    await message.reply(admins_text, parse_mode="Markdown")


@router.message(Command("ban"))
async def cmd_ban(message: Message):
    """Handle /ban command (Admin/Owner only)."""
    user_id = message.from_user.id
    
    # Check if user is admin
    if not config.is_admin(user_id):
        log_admin_command(user_id, "UNAUTHORIZED BAN ATTEMPT", 0)
        await message.reply(
            "❌ *Error*: Unauthorized action. Only administrators can use this command.",
            parse_mode="Markdown"
        )
        return
        
    args = message.text.split()
    if len(args) != 2:
        await message.reply(
            "❌ *Usage*: `/ban <user_id>`\n"
            "Example: `/ban 123456789`",
            parse_mode="Markdown"
        )
        return
        
    try:
        target_id = int(args[1])
    except ValueError:
        await message.reply(
            "❌ *Error*: Invalid user ID. ID must be a number.",
            parse_mode="Markdown"
        )
        return
        
    # Can't ban owner
    if config.is_owner(target_id):
        await message.reply(
            "❌ *Error*: Cannot ban the owner.",
            parse_mode="Markdown"
        )
        return
        
    # Prevent banning other admins
    if config.is_admin(target_id):
        await message.reply(
            "❌ *Error*: Cannot ban another administrator.",
            parse_mode="Markdown"
        )
        return
        
    await db.ban_user(target_id)
    
    # Log to console
    log_admin_command(user_id, f"Banned User", target_id)
    
    # Log to channel
    if config.log_channel_id:
        try:
            await message.bot.send_message(
                config.log_channel_id,
                f"🚫 *User Banned*\n\n"
                f"🛡 *Admin:* `{user_id}`\n"
                f"👤 *Banned User:* `{target_id}`",
                parse_mode="Markdown"
            )
        except Exception:
            pass

    await message.reply(
        "✅ *↯ 〔 USER BANNED 〕 ↯*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 *User ID:* `{target_id}` has been banned successfully.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="Markdown"
    )


@router.message(Command("unban"))
async def cmd_unban(message: Message):
    """Handle /unban command (Admin/Owner only)."""
    user_id = message.from_user.id
    
    # Check if user is admin
    if not config.is_admin(user_id):
        log_admin_command(user_id, "UNAUTHORIZED UNBAN ATTEMPT", 0)
        await message.reply(
            "❌ *Error*: Unauthorized action. Only administrators can use this command.",
            parse_mode="Markdown"
        )
        return
        
    args = message.text.split()
    if len(args) != 2:
        await message.reply(
            "❌ *Usage*: `/unban <user_id>`\n"
            "Example: `/unban 123456789`",
            parse_mode="Markdown"
        )
        return
        
    try:
        target_id = int(args[1])
    except ValueError:
        await message.reply(
            "❌ *Error*: Invalid user ID. ID must be a number.",
            parse_mode="Markdown"
        )
        return
        
    await db.unban_user(target_id)
    
    # Log to console
    log_admin_command(user_id, f"Unbanned User", target_id)
    
    # Log to channel
    if config.log_channel_id:
        try:
            await message.bot.send_message(
                config.log_channel_id,
                f"✅ *User Unbanned*\n\n"
                f"🛡 *Admin:* `{user_id}`\n"
                f"👤 *Unbanned User:* `{target_id}`",
                parse_mode="Markdown"
            )
        except Exception:
            pass

    await message.reply(
        "✅ *↯ 〔 USER UNBANNED 〕 ↯*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 *User ID:* `{target_id}` has been unbanned successfully.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="Markdown"
    )


@router.message(Command("users"))
async def cmd_users(message: Message):
    """Handle /users command (Admin/Owner only)."""
    user_id = message.from_user.id
    
    # Check if user is admin
    if not config.is_admin(user_id):
        log_admin_command(user_id, "UNAUTHORIZED USERS VIEW ATTEMPT", 0)
        await message.reply(
            "❌ *Error*: Unauthorized action. Only administrators can use this command.",
            parse_mode="Markdown"
        )
        return
        
    users = await db.get_all_users()
    banned = await db.get_banned_users()
    
    text = (
        "📊 *↯ 〔 USER DATABASE STATISTICS 〕 ↯*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 *Total Registered:* `{len(users)}`\n"
        f"🚫 *Banned Users:* `{len(banned)}`\n\n"
        "*Recent Database Users:*\n"
    )
    
    # Show first 15 users
    for idx, user in enumerate(users[:15]):
        username = user.get("username", "N/A")
        role = user.get("role", "member")
        is_last = (idx == len(users[:15]) - 1 and len(users) <= 15)
        prefix = " └" if is_last else " ├"
        text += f"{prefix} `{user['user_id']}` - @{username} ({role})\n"
        
    if len(users) > 15:
        text += f" └ ... and {len(users) - 15} more registered users.\n"
        
    text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    await message.reply(text, parse_mode="Markdown")