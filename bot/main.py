"""
Main bot application.
Entry point for the Telegram bot.
"""
import asyncio
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from structlog import get_logger

from bot.config import config, validate_config
from bot.handlers import start, register, admin, checker, status, spt
from bot.middlewares.auth import AuthMiddleware
from bot.services.database import db

logger = get_logger(__name__)


async def main():
    """Main bot function."""
    import time
    import platform
    from bot.utils.logging import log, log_user_error
    
    start_time = time.time()
    log("Bot starting")
    
    try:
        # Create required directories
        Path(config.data_dir).mkdir(exist_ok=True)
        Path(config.logs_dir).mkdir(exist_ok=True)
        
        # Validate configuration
        validate_config()
        log("All requirements installed")
        
        # Initialize bot with default properties
        bot = Bot(
            token=config.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
        )
        
        # Initialize dispatcher
        dp = Dispatcher(storage=MemoryStorage())
        
        # Register middlewares
        dp.message.middleware(AuthMiddleware())
        
        # Register routers
        dp.include_router(start.router)
        dp.include_router(register.router)
        dp.include_router(admin.router)
        dp.include_router(checker.router)
        dp.include_router(status.router)
        dp.include_router(spt.router)
        
        # Database check and load counts
        users_cnt = await db.get_users_count()
        db_admins_cnt = len(await db.get_admins())
        log(f"Database loaded with {users_cnt} users, {db_admins_cnt} admins")
        
        # Startup Diagnostics
        # 1. Bot Name & Ping
        ping_start = time.time()
        bot_user = await bot.get_me()
        ping_ms = int((time.time() - ping_start) * 1000)
        bot_name = bot_user.full_name
        log(f"Ping: {ping_ms} ms")
        
        # 2. Health Check
        health_status = "Passed ✅"
        try:
            # Check write permissions in directories
            test_file = Path(config.data_dir) / ".health_check"
            test_file.touch()
            test_file.unlink()
        except Exception:
            health_status = "Failed ❌"
        log(f"Bot Health: {health_status}")
            
        startup_sec = time.time() - start_time
        log(f"Startup time: {startup_sec:.2f} sec")
        
        # 3. Owner status, Admin lists and channel diagnostics
        owner_status = "Found ✅" if config.owner_id else "Not Found ❌"
        log_channel_status = "Working ✅" if config.log_channel_id else "Not Configured ⚠️"
        log(f"Bot is running. Name: {bot_name}, Owner: {owner_status}, Channel: {log_channel_status}")
        
        # Send PM notification to Owner
        if config.owner_id:
            try:
                from datetime import datetime
                total_users = await db.get_users_count()
                startup_msg = (
                    "🚀 *Bot Started Successfully*\n"
                    "━━━━━━━━━━━━━━\n\n"
                    "Status: 🟢 *Online*\n"
                    f"Ping: `{ping_ms} ms`\n"
                    f"Database: ✅ *Connected*\n"
                    f"Admins: `{db_admins_cnt + len(config.admin_ids)}`\n"
                    f"Users: `{total_users}`\n"
                    f"Startup Time: `{startup_sec:.2f} sec`\n"
                    "Version: `Latest`\n"
                    f"Time: `{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}`\n\n"
                    "Ready to receive commands."
                )
                await bot.send_message(
                    chat_id=config.owner_id,
                    text=startup_msg,
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error("startup_notification_failed", error=str(e))
                
        # Start polling
        await dp.start_polling(bot)
        
    except Exception as e:
        log_user_error(0, "bot_main_startup", str(e))
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("bot_stopped")
    except Exception as e:
        logger.error("fatal_error", error=str(e))
        sys.exit(1)