"""
Authentication middleware for the bot.
Ensures users are registered and not banned.
"""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from bot.services.database import db
from bot.config import config
from structlog import get_logger

logger = get_logger(__name__)


class AuthMiddleware(BaseMiddleware):
    """Authentication middleware."""
    
    # Commands that don't require registration
    PUBLIC_COMMANDS = ["/start", "/help", "/register"]
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        """Process middleware."""
        
        # Skip for non-message events
        if not isinstance(event, Message):
            return await handler(event, data)
        
        user_id = event.from_user.id
        
        # Check if banned
        if await db.is_banned(user_id):
            await event.reply(
                "🚫 *You are banned from using this bot.*\n\n"
                "Contact the administrator if you think this is a mistake.",
                parse_mode="Markdown"
            )
            return
        
        # Auto-registration
        if not await db.user_exists(user_id):
            await db.add_user(
                user_id=user_id,
                username=event.from_user.username or "",
                first_name=event.from_user.first_name,
                last_name=event.from_user.last_name or ""
            )
            from bot.utils.logging import log_new_user_registered
            log_new_user_registered(
                user_id=user_id,
                username=event.from_user.username or "",
                method="automatic",
                chat_id=event.chat.id,
                chat_title=event.chat.title or ""
            )
            
            # Log registration to channel if config exists
            if config.log_channel_id:
                try:
                    from datetime import datetime
                    log_text = (
                        f"🆕 *Automatic Registration*\n\n"
                        f"👤 *User:* {event.from_user.first_name} {event.from_user.last_name or ''}\n"
                        f"🆔 *ID:* `{user_id}`\n"
                        f"📝 *Username:* @{event.from_user.username or 'N/A'}\n"
                        f"📅 *Date:* {datetime.utcnow().strftime('%Y-%m-%d')}\n"
                        f"⏰ *Time:* {datetime.utcnow().strftime('%H:%M:%S')} UTC"
                    )
                    await event.bot.send_message(
                        config.log_channel_id,
                        log_text,
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    logger.error("log_channel_error", error=str(e))
        
        # Log command usage
        if event.text and event.text.startswith("/"):
            from bot.utils.logging import log_user_command
            log_user_command(
                user_id=user_id,
                command=event.text.split()[0],
                chat_id=event.chat.id,
                chat_title=event.chat.title or ""
            )
            
        return await handler(event, data)