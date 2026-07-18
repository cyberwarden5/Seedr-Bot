"""Registration handler."""
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from bot.services.database import db
from bot.config import config
from structlog import get_logger
from datetime import datetime

logger = get_logger(__name__)
router = Router()


@router.message(Command("register"))
async def cmd_register(message: Message):
    """Handle /register command."""
    user = message.from_user
    user_id = user.id
    
    # Check if already registered
    if await db.user_exists(user_id):
        await message.reply(
            "✅ *↯ 〔 ALREADY REGISTERED 〕 ↯*\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "👤 You are already registered with the checker bot.\n"
            "📖 Use /help to see all available commands.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━",
            parse_mode="Markdown"
        )
        return
    
    # Check if banned
    if await db.is_banned(user_id):
        await message.reply(
            "🚫 *↯ 〔 REGISTRATION DENIED 〕 ↯*\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🚫 *You are banned from using this bot and cannot register.*\n\n"
            "━━━━━━━━━━━━━━━━━━━━━",
            parse_mode="Markdown"
        )
        return
    
    # Register user
    await db.add_user(
        user_id=user_id,
        username=user.username or "",
        first_name=user.first_name,
        last_name=user.last_name or ""
    )
    
    # Send confirmation
    await message.reply(
        "✅ *↯ 〔 REGISTRATION SUCCESSFUL 〕 ↯*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 *User ID:* `{user_id}`\n"
        f"👑 *Role:* `member`\n"
        f"📅 *Date:* `{datetime.utcnow().strftime('%Y-%m-%d')}`\n"
        f"⏰ *Time:* `{datetime.utcnow().strftime('%H:%M:%S')} UTC`\n\n"
        "🎉 *Welcome!* You can now use all the bot's features.\n\n"
        "📌 *Your Membership Limits:*\n"
        f" ├ 📁 Max File Size: `{config.max_file_size_mb} MB`\n"
        f" ├ 📊 Max Combos / Check: `{config.max_combos_per_user} lines`\n"
        " └ ⏳ Max Concurrent Tasks: `1` (Owner/Admins have unlimited)\n\n"
        "📖 Use /help to see the commands list.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="Markdown"
    )
    
    # Log to channel
    if config.log_channel_id:
        try:
            log_text = (
                f"🆕 *New Registration*\n\n"
                f"👤 *User:* {user.first_name} {user.last_name or ''}\n"
                f"🆔 *ID:* `{user_id}`\n"
                f"📝 *Username:* @{user.username or 'N/A'}\n"
                f"📅 *Date:* {datetime.utcnow().strftime('%Y-%m-%d')}\n"
                f"⏰ *Time:* {datetime.utcnow().strftime('%H:%M:%S')} UTC"
            )
            await message.bot.send_message(
                config.log_channel_id,
                log_text,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error("log_channel_error", error=str(e))
    
    logger.info("user_registered", user_id=user_id)