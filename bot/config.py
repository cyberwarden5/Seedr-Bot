"""
Bot configuration module.
Handles environment variables and settings.
"""
import os
from dataclasses import dataclass, field
from typing import List, Set
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Bot configuration settings."""
    
    # Bot settings
    bot_token: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    owner_id: int = field(default_factory=lambda: int(os.getenv("OWNER_ID", "0")))
    admin_ids: List[int] = field(default_factory=lambda: [
        int(id_str.strip()) for id_str in os.getenv("ADMIN_IDS", "").split(",") if id_str.strip()
    ])
    
    # Logging
    log_channel_id: int = field(default_factory=lambda: int(os.getenv("LOG_CHANNEL_ID", "0")))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    
    # Limits
    max_combos_per_user: int = field(default_factory=lambda: int(os.getenv("MAX_COMBOS_PER_USER", "500")))
    max_file_size_mb: int = field(default_factory=lambda: int(os.getenv("MAX_FILE_SIZE_MB", "5")))
    max_concurrent_tasks: int = field(default_factory=lambda: int(os.getenv("MAX_CONCURRENT_TASKS", "3")))
    
    # Checker settings
    checker_timeout: int = field(default_factory=lambda: int(os.getenv("CHECKER_TIMEOUT", "30")))
    rate_limit_delay: float = field(default_factory=lambda: float(os.getenv("RATE_LIMIT_DELAY", "0.5")))
    
    # Paths
    data_dir: str = "data"
    logs_dir: str = "logs"
    
    def get_admin_set(self) -> Set[int]:
        """Get set of admin IDs including owner and DB admins."""
        from bot.services.database import db
        admins = set(self.admin_ids)
        admins.add(self.owner_id)
        try:
            admins.update(db.db_admins)
        except Exception:
            pass
        return admins
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin or owner."""
        return user_id in self.get_admin_set()
    
    def is_owner(self, user_id: int) -> bool:
        """Check if user is owner."""
        return user_id == self.owner_id


# Create the config instance AFTER the class definition
config = Config()


def validate_config() -> bool:
    """Validate configuration."""
    if not config.bot_token or config.bot_token == "YOUR_BOT_TOKEN_HERE":
        raise ValueError("BOT_TOKEN is required in .env file. Edit .env and add your bot token.")
    if not config.owner_id or config.owner_id == 123456789:
        raise ValueError("OWNER_ID is required in .env file. Edit .env and add your Telegram user ID.")
    return True