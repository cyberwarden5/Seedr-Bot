"""
Helper utilities for the bot.
"""
import re
import hashlib
from typing import List, Tuple, Set
from datetime import datetime, timedelta
import asyncio


def validate_combo(combo: str) -> Tuple[bool, str, str]:
    """
    Validate combo format (email:password).
    
    Args:
        combo: Combo string to validate
        
    Returns:
        Tuple of (is_valid, email, password)
    """
    if ':' not in combo:
        return False, "", ""
    
    parts = combo.split(':', 1)
    email = parts[0].strip()
    password = parts[1].strip()
    
    # Basic email validation
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return False, "", ""
    
    # Password should not be empty
    if not password:
        return False, "", ""
    
    return True, email, password


def parse_combo_file(content: str) -> Tuple[List[str], int, int, int]:
    """
    Parse combo file content.
    
    Args:
        content: File content
        
    Returns:
        Tuple of (valid_combos, total_lines, invalid_lines, duplicates_removed)
    """
    lines = content.strip().split('\n')
    total_lines = len(lines)
    
    # Remove empty lines
    lines = [line.strip() for line in lines if line.strip()]
    
    # Remove duplicates while preserving order
    seen = set()
    unique_lines = []
    for line in lines:
        if line not in seen:
            seen.add(line)
            unique_lines.append(line)
    
    duplicates_removed = total_lines - len(unique_lines)
    
    # Validate combos
    valid_combos = []
    invalid_lines = 0
    
    for line in unique_lines:
        is_valid, _, _ = validate_combo(line)
        if is_valid:
            valid_combos.append(line)
        else:
            invalid_lines += 1
    
    return valid_combos, total_lines, invalid_lines, duplicates_removed


def format_time(seconds: float) -> str:
    """Format seconds to HH:MM:SS."""
    if seconds < 0:
        return "00:00:00"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def format_bytes(bytes_value: int) -> str:
    """Format bytes to human readable format."""
    if bytes_value == 0:
        return "0 B"
    
    gb = bytes_value / (1024 ** 3)
    if gb >= 1:
        return f"{gb:.2f} GB"
    
    mb = bytes_value / (1024 ** 2)
    if mb >= 1:
        return f"{mb:.2f} MB"
    
    kb = bytes_value / 1024
    return f"{kb:.2f} KB"


def calculate_cpm(processed: int, elapsed_seconds: float) -> float:
    """Calculate checks per minute."""
    if elapsed_seconds == 0:
        return 0.0
    return (processed / elapsed_seconds) * 60


def estimate_remaining(remaining: int, cpm: float) -> float:
    """Estimate remaining time in seconds."""
    if cpm == 0:
        return 0.0
    return (remaining / cpm) * 60


class AsyncRateLimiter:
    """Simple async rate limiter."""
    
    def __init__(self, delay: float):
        """
        Initialize rate limiter.
        
        Args:
            delay: Delay between operations in seconds
        """
        self.delay = delay
        self.last_call = 0
        self._lock = asyncio.Lock()
    
    async def wait(self):
        """Wait if needed to respect rate limit."""
        async with self._lock:
            now = datetime.utcnow().timestamp()
            time_since_last = now - self.last_call
            
            if time_since_last < self.delay:
                await asyncio.sleep(self.delay - time_since_last)
            
            self.last_call = datetime.utcnow().timestamp()