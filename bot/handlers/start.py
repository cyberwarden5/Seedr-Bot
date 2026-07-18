"""Start and help command handlers."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from bot.keyboards.inline import get_start_keyboard, get_check_keyboard
from bot.config import config

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Handle /start command."""
    user = message.from_user
    
    welcome_text = (
        "👑 *↯ 〔 COMBO CHECKER ENGINE 〕 ↯*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👋 *Welcome, {user.first_name}!*\n\n"
        "⚡ *Premium Seedr.cc Account Verifier*\n\n"
        "📂 *Core Features:*\n"
        " ├ 👤 Single Account Check\n"
        " ├ 📥 Bulk File Processing\n"
        " └ 📊 Live CPM & Progress Stats\n\n"
        "⚠ *Authorized Testing Only!*\n"
        "Please ensure you own or have permission to test the credentials.\n\n"
        "⚔ *Quick Start:*\n"
        " ├ Use /chk to test a single account\n"
        " └ Use /txt to upload combo files\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📖 Use /help for a detailed commands menu."
    )
    
    await message.reply(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=get_start_keyboard()
    )


# Define global help menu text so it can be reused in callback
HELP_MENU_TEXT = (
    "📚 *↯ 〔 HELP & COMMANDS 〕 ↯*\n"
    "━━━━━━━━━━━━━━━━━━━━━\n\n"
    "👤 *User Commands:*\n"
    " ├ /start ⤖ Wake up the bot\n"
    " ├ /help ⤖ Show this menu\n"
    " ├ /register ⤖ Register account\n"
    " ├ /chk <email:pass> ⤖ Check single account\n"
    " ├ /txt ⤖ Upload bulk combo file\n"
    " ├ /spt <amount> ⤖ Split combo file (reply to TXT)\n"
    " └ /cancel ⤖ Cancel running check task\n\n"
    "🛡 *Admin Commands:*\n"
    " ├ /status ⤖ Bot & System status\n"
    " ├ /users ⤖ Show registered users\n"
    " ├ /ban <user_id> ⤖ Ban user\n"
    " └ /unban <user_id> ⤖ Unban user\n\n"
    "👑 *Owner Commands:*\n"
    " ├ /addadmin <user_id> ⤖ Add an administrator\n"
    " ├ /removeadmin <user_id> ⤖ Remove an administrator\n"
    " └ /admins ⤖ List all administrators\n\n"
    "━━━━━━━━━━━━━━━━━━━━━\n"
    "⚡ Powered by Seedr Checker Engine"
)


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command."""
    await message.reply(HELP_MENU_TEXT, parse_mode="Markdown")


@router.callback_query(F.data == "help")
async def callback_help(callback: CallbackQuery):
    """Handle help callback by editing the start message."""
    try:
        await callback.message.edit_text(HELP_MENU_TEXT, parse_mode="Markdown")
    except Exception:
        # Fallback if message can't be edited
        await callback.message.reply(HELP_MENU_TEXT, parse_mode="Markdown")
    await callback.answer()