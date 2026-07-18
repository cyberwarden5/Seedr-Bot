"""Split command handler."""
import os
import time
from pathlib import Path
from aiogram import Router
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command

from bot.utils.helpers import validate_combo
from bot.utils.logging import log_split_command, log_user_error

router = Router()


@router.message(Command("spt"))
async def cmd_spt(message: Message):
    """Handle /spt <amount> command."""
    user_id = message.from_user.id
    
    # Check if message is a reply to another message
    if not message.reply_to_message:
        await message.reply(
            "❌ *Error*: Please reply to a `.txt` file containing combos to split.\n"
            "Example: Reply to a file with `/spt 500`",
            parse_mode="Markdown"
        )
        return
        
    # Check if the replied message has a document
    document = message.reply_to_message.document
    if not document or not document.file_name.endswith('.txt'):
        await message.reply(
            "❌ *Error*: The replied message must contain a valid `.txt` file.",
            parse_mode="Markdown"
        )
        return
        
    args = message.text.split()
    if len(args) < 2:
        await message.reply(
            "❌ *Usage*: `/spt <amount>`\n"
            "Example: Reply to a file with `/spt 500`",
            parse_mode="Markdown"
        )
        return
        
    try:
        amount = int(args[1])
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.reply(
            "❌ *Error*: Amount must be a positive integer.\n"
            "Example: `/spt 500`",
            parse_mode="Markdown"
        )
        return
        
    start_time = time.time()
    
    # Download file
    temp_dir = Path("temp")
    temp_dir.mkdir(exist_ok=True)
    temp_path = temp_dir / f"spt_{user_id}_{int(start_time)}_{document.file_name}"
    
    # Send download status
    status_msg = await message.reply("📥 *Downloading file...*", parse_mode="Markdown")
    
    try:
        await message.bot.download(document, destination=str(temp_path))
        
        await status_msg.edit_text("📄 *Parsing and cleaning combos...*", parse_mode="Markdown")
        
        # Read content
        with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        lines = content.splitlines()
        original_lines_count = len(lines)
        
        # Extract unique valid lines
        unique_valid = []
        seen = set()
        
        for line in lines:
            cleaned = line.strip()
            if not cleaned:
                continue
            is_valid, _, _ = validate_combo(cleaned)
            if is_valid:
                if cleaned not in seen:
                    seen.add(cleaned)
                    unique_valid.append(cleaned)
                    
        removed_duplicates = original_lines_count - len(unique_valid)
        
        if not unique_valid:
            await status_msg.edit_text(
                "❌ *Error*: No valid combos found in the file.\n"
                "Ensure lines are formatted as `email:password`.",
                parse_mode="Markdown"
            )
            # Cleanup temp file
            if temp_path.exists():
                os.remove(temp_path)
            return
            
        # Split into chunks
        chunks = [unique_valid[i:i + amount] for i in range(0, len(unique_valid), amount)]
        files_created = len(chunks)
        
        await status_msg.edit_text(f"📦 *Creating {files_created} split file(s)...*", parse_mode="Markdown")
        
        created_files_paths = []
        # Generate files
        for idx, chunk in enumerate(chunks):
            part_name = f"part_{idx + 1}.txt"
            part_path = temp_dir / f"spt_{user_id}_{int(start_time)}_{part_name}"
            with open(part_path, 'w', encoding='utf-8') as pf:
                pf.write('\n'.join(chunk) + '\n')
            created_files_paths.append((part_name, part_path))
            
        await status_msg.edit_text("📤 *Sending split files...*", parse_mode="Markdown")
        
        # Send each split file
        for part_name, part_path in created_files_paths:
            await message.reply_document(
                FSInputFile(str(part_path)),
                caption=f"📂 `{part_name}` | 📝 Lines: `{len(chunks[created_files_paths.index((part_name, part_path))])}`"
            )
            
        elapsed_time = time.time() - start_time
        
        # Display Summary
        summary_text = (
            "✅ *↯ 〔 FILE SPLIT COMPLETE 〕 ↯*\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📂 *Original Name:* `{document.file_name}`\n"
            f"📝 *Original Lines:* `{original_lines_count}`\n"
            f"🎯 *Unique Valid:* `{len(unique_valid)}`\n"
            f"🔄 *Duplicates/Invalid Removed:* `{removed_duplicates}`\n"
            f"📦 *Files Created:* `{files_created}`\n"
            f"⏱ *Time Taken:* `{elapsed_time:.2f} sec`\n\n"
            "━━━━━━━━━━━━━━━━━━━━━"
        )
        
        await status_msg.edit_text(summary_text, parse_mode="Markdown")
        
        # Log to console
        log_split_command(
            user_id=user_id,
            original=original_lines_count,
            duplicates=removed_duplicates,
            unique=len(unique_valid),
            output_files=files_created,
            elapsed_time=elapsed_time,
            chat_id=message.chat.id,
            chat_title=message.chat.title or ""
        )
        
        # Cleanup
        for _, part_path in created_files_paths:
            if part_path.exists():
                os.remove(part_path)
                
    except Exception as e:
        log_user_error(user_id, f"/spt {amount}", str(e), message.chat.id, message.chat.title or "")
        try:
            await status_msg.edit_text(
                f"❌ *Error during splitting operation!*\n\n`{str(e)}`",
                parse_mode="Markdown"
            )
        except Exception:
            pass
            
    finally:
        # Cleanup original temp file
        if temp_path.exists():
            os.remove(temp_path)
