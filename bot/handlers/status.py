"""Status and statistics handler."""
import psutil
import platform
import time
from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from bot.services.database import db
from bot.config import config

router = Router()

# Bot start time
BOT_START_TIME = time.time()


@router.message(Command("status"))
async def cmd_status(message: Message):
    """Handle /status command."""
    user_id = message.from_user.id
    
    # Check authorization
    if not config.is_admin(user_id):
        # Log denied action
        from bot.utils.logging import log_admin_command
        log_admin_command(user_id, "UNAUTHORIZED STATUS ATTEMPT", 0)
        await message.reply(
            "❌ *Error*: Unauthorized action. Only administrators can use this command.",
            parse_mode="Markdown"
        )
        return

    # System stats
    cpu_percent = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Bot stats
    bot_uptime = time.time() - BOT_START_TIME
    total_users = await db.get_users_count()
    active_tasks = len(await db.get_active_tasks())
    admins_count = len(await db.get_admins()) + len(config.admin_ids)
    
    # Format uptime
    hours = int(bot_uptime // 3600)
    minutes = int((bot_uptime % 3600) // 60)
    seconds = int(bot_uptime % 60)
    uptime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    status_text = (
        "📊 *Base System & Bot Metrics*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "💻 *System Diagnostics:*\n"
        f" ├ 🖥 CPU Load: `{cpu_percent}%`\n"
        f" ├ 💾 Memory (RAM): `{ram.percent}%` ({ram.used // (1024**3)}/{ram.total // (1024**3)} GB)\n"
        f" ├ 💿 Disk Space: `{disk.percent}%` ({disk.free // (1024**3)} GB free)\n"
        f" ├ 🐍 Python Engine: `v{platform.python_version()}`\n"
        f" └ 💻 OS Environment: `{platform.system()} {platform.release()}`\n\n"
        "🤖 *Bot Operations:*\n"
        f" ├ ⏱ Uptime Duration: `{uptime_str}`\n"
        f" ├ 👥 Registered Users: `{total_users}`\n"
        f" ├ 🛡 Admin Count: `{admins_count}`\n"
        f" ├ ⚡ Active Checkers: `{active_tasks}`\n"
        f" └ 📅 Clock: `{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    
    await message.reply(status_text, parse_mode="Markdown")