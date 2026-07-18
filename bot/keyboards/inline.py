"""Inline keyboards for the bot."""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_start_keyboard() -> InlineKeyboardMarkup:
    """Get start keyboard."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="📝 Register", 
        callback_data="register"
    ))
    builder.add(InlineKeyboardButton(
        text="❓ Help", 
        callback_data="help"
    ))
    builder.adjust(1)
    return builder.as_markup()


def get_check_keyboard() -> InlineKeyboardMarkup:
    """Get checker keyboard."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="🔍 Single Check", 
        callback_data="single_check"
    ))
    builder.add(InlineKeyboardButton(
        text="📁 Bulk Check", 
        callback_data="bulk_check"
    ))
    builder.add(InlineKeyboardButton(
        text="❌ Cancel Task", 
        callback_data="cancel_task"
    ))
    builder.adjust(2, 1)
    return builder.as_markup()


def get_cancel_keyboard(task_id: str = "") -> InlineKeyboardMarkup:
    """Get cancel keyboard."""
    builder = InlineKeyboardBuilder()
    callback_data = f"cancel_task:{task_id}" if task_id else "cancel_task"
    builder.add(InlineKeyboardButton(
        text="❌ Cancel", 
        callback_data=callback_data
    ))
    return builder.as_markup()


def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Get admin keyboard."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="👥 Users", 
        callback_data="admin_users"
    ))
    builder.add(InlineKeyboardButton(
        text="📊 Stats", 
        callback_data="admin_stats"
    ))
    builder.add(InlineKeyboardButton(
        text="🚫 Ban User", 
        callback_data="admin_ban"
    ))
    builder.add(InlineKeyboardButton(
        text="✅ Unban User", 
        callback_data="admin_unban"
    ))
    builder.adjust(2)
    return builder.as_markup()