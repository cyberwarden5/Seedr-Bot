"""
Structured logging module for the bot.
Outputs clean, professional terminal logs in simple line-based format.
"""
from datetime import datetime

def get_log_prefix() -> str:
    """Get the log timestamp prefix."""
    return f"[Info:{datetime.now().strftime('%Y-%m-%d-%H:%M:%S')}]"

def log(msg: str):
    """Print a single log line to stdout."""
    print(f"{get_log_prefix()} {msg}", flush=True)

def log_startup(
    python_version: str,
    bot_name: str,
    owner_status: str,
    admins_str: str,
    db_status: str,
    log_channel_status: str,
    health_status: str,
    ping_ms: int,
    startup_sec: float,
    users_count: int,
    db_admins_count: int
):
    """Log bot startup details."""
    log("Bot starting")
    log("All requirements installed")
    log(f"Database loaded with {users_count} users, {db_admins_count} admins")
    log(f"Ping: {ping_ms} ms")
    log(f"Bot Health: {health_status}")
    log(f"Startup time: {startup_sec:.2f} sec")
    log(f"Bot is running. Name: {bot_name}, Owner: {owner_status}, Channel: {log_channel_status}")

def log_new_user_registered(user_id: int, username: str, method: str = "automatic", chat_id: int = 0, chat_title: str = ""):
    """Log when a new user is registered."""
    chat_info = f" from Group '{chat_title}' ({chat_id})" if chat_id and chat_id != user_id else " in Private Chat"
    log(f"New user registered. ID: {user_id}, Username: @{username or 'N/A'} ({method}){chat_info}")

def log_user_command(user_id: int, command: str, chat_id: int = 0, chat_title: str = ""):
    """Log user command usage."""
    chat_info = f" in Group '{chat_title}' ({chat_id})" if chat_id and chat_id != user_id else " in Private Chat"
    log(f"User {user_id} used {command} command{chat_info}")

def log_user_error(user_id: int, command: str, error_msg: str, chat_id: int = 0, chat_title: str = ""):
    """Log errors encountered by users."""
    chat_info = f" in Group '{chat_title}' ({chat_id})" if chat_id and chat_id != user_id else " in Private Chat"
    log(f"User {user_id} got error while using {command} command{chat_info}. Error: [{error_msg}]")

def log_user_action(user_id: int, action: str, chat_id: int = 0, chat_title: str = ""):
    """Log user actions (like file uploads, cancellations)."""
    chat_info = f" in Group '{chat_title}' ({chat_id})" if chat_id and chat_id != user_id else " in Private Chat"
    log(f"User {user_id} {action}{chat_info}")

def log_file_check_start(user_id: int, filename: str, task_id: str, total_lines: int, chat_id: int = 0, chat_title: str = ""):
    """Log when a user starts checking a bulk combo file."""
    chat_info = f" in Group '{chat_title}' ({chat_id})" if chat_id and chat_id != user_id else " in Private Chat"
    log(f"User {user_id} started file check with {filename}{chat_info}. Combo-Id: {task_id}, total lines: {total_lines}")

def log_file_check_finish(user_id: int, task_id: str, hits: int, processed: int, status: str = "finished", chat_id: int = 0, chat_title: str = ""):
    """Log when a combo checker task completes or gets cancelled."""
    chat_info = f" in Group '{chat_title}' ({chat_id})" if chat_id and chat_id != user_id else " in Private Chat"
    log(f"User {user_id} task {status}{chat_info}. id: {task_id}, processed: {processed}, hits: {hits}")

def log_admin_command(admin_id: int, action: str, target_id: int):
    """Log admin management actions."""
    log(f"Admin/owner {admin_id} performed action: {action} on target {target_id}")

def log_split_command(user_id: int, original: int, duplicates: int, unique: int, output_files: int, elapsed_time: float, chat_id: int = 0, chat_title: str = ""):
    """Log split command execution."""
    chat_info = f" in Group '{chat_title}' ({chat_id})" if chat_id and chat_id != user_id else " in Private Chat"
    log(f"User {user_id} split combo file: original {original}, duplicates {duplicates}, unique {unique}, output files {output_files}, time: {elapsed_time:.1f} sec{chat_info}")
