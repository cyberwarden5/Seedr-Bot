"""
Simple JSON-based database service.
Stores user data and banned users in JSON files.
"""
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
import asyncio
from structlog import get_logger

logger = get_logger(__name__)


class JsonDatabase:
    """Simple JSON file-based database."""
    
    def __init__(self, data_dir: str = "data"):
        """
        Initialize database.
        
        Args:
            data_dir: Directory for JSON data files
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.users_file = self.data_dir / "users.json"
        self.banned_file = self.data_dir / "banned.json"
        self.tasks_file = self.data_dir / "tasks.json"
        self.admins_file = self.data_dir / "admins.json"
        
        # Initialize files if they don't exist
        self._init_file(self.users_file, {})
        self._init_file(self.banned_file, [])
        self._init_file(self.tasks_file, {})
        self._init_file(self.admins_file, [])
        
        # Load data into memory
        self.users: Dict[str, Any] = {}
        self.banned: List[int] = []
        self.tasks: Dict[str, Any] = {}
        self.db_admins: List[int] = []
        
        self._load_all()
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
    
    def _init_file(self, file_path: Path, default_data: Any):
        """Initialize a JSON file with default data if it doesn't exist."""
        if not file_path.exists():
            with open(file_path, 'w') as f:
                json.dump(default_data, f, indent=2)
    
    def _load_all(self):
        """Load all data from files."""
        try:
            with open(self.users_file, 'r') as f:
                self.users = json.load(f)
        except Exception as e:
            logger.error("load_users_failed", error=str(e))
            self.users = {}
        
        try:
            with open(self.banned_file, 'r') as f:
                self.banned = json.load(f)
        except Exception as e:
            logger.error("load_banned_failed", error=str(e))
            self.banned = []
        
        try:
            with open(self.tasks_file, 'r') as f:
                self.tasks = json.load(f)
        except Exception as e:
            logger.error("load_tasks_failed", error=str(e))
            self.tasks = {}

        try:
            with open(self.admins_file, 'r') as f:
                self.db_admins = json.load(f)
        except Exception as e:
            logger.error("load_admins_failed", error=str(e))
            self.db_admins = []

        # Preload owner in memory/database on startup
        try:
            from bot.config import config
            owner_id_str = str(config.owner_id)
            if owner_id_str not in self.users:
                self.users[owner_id_str] = {
                    "user_id": config.owner_id,
                    "username": "owner",
                    "first_name": "Owner",
                    "last_name": "",
                    "registered_at": datetime.utcnow().isoformat(),
                    "total_checks": 0,
                    "total_hits": 0,
                    "total_dead": 0,
                    "total_invalid": 0,
                    "current_task_id": None
                }
            
            # Always ensure owner has proper role, status, permissions
            self.users[owner_id_str].update({
                "role": "owner",
                "status": "active",
                "permissions": "Full access",
                "last_active": datetime.utcnow().isoformat()
            })
            
            # Write to users file synchronously since it's init
            with open(self.users_file, 'w') as f:
                json.dump(self.users, f, indent=2, default=str)
        except Exception as e:
            logger.error("preload_owner_failed", error=str(e))
            
        # Cleanup any leftover active tasks from a previous run/crash
        try:
            tasks_modified = False
            for t_id, task in self.tasks.items():
                if task.get("status") == "running":
                    task["status"] = "stopped"
                    task["completed_at"] = datetime.utcnow().isoformat()
                    tasks_modified = True
                    
            users_modified = False
            for u_id, user in self.users.items():
                if user.get("current_task_id"):
                    user["current_task_id"] = None
                    users_modified = True
                    
            if tasks_modified:
                with open(self.tasks_file, 'w') as f:
                    json.dump(self.tasks, f, indent=2, default=str)
            if users_modified:
                with open(self.users_file, 'w') as f:
                    json.dump(self.users, f, indent=2, default=str)
        except Exception as e:
            logger.error("cleanup_leftover_tasks_failed", error=str(e))
    
    async def _save_users(self):
        """Save users to file."""
        async with self._lock:
            try:
                with open(self.users_file, 'w') as f:
                    json.dump(self.users, f, indent=2, default=str)
            except Exception as e:
                logger.error("save_users_failed", error=str(e))
    
    async def _save_banned(self):
        """Save banned list to file."""
        async with self._lock:
            try:
                with open(self.banned_file, 'w') as f:
                    json.dump(self.banned, f, indent=2)
            except Exception as e:
                logger.error("save_banned_failed", error=str(e))
    
    async def _save_tasks(self):
        """Save tasks to file."""
        async with self._lock:
            try:
                with open(self.tasks_file, 'w') as f:
                    json.dump(self.tasks, f, indent=2, default=str)
            except Exception as e:
                logger.error("save_tasks_failed", error=str(e))

    async def _save_admins(self):
        """Save admins list to file."""
        async with self._lock:
            try:
                with open(self.admins_file, 'w') as f:
                    json.dump(self.db_admins, f, indent=2)
            except Exception as e:
                logger.error("save_admins_failed", error=str(e))
    
    # User Methods
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        return self.users.get(str(user_id))
    
    async def add_user(self, user_id: int, username: str, first_name: str, last_name: str = "") -> Dict[str, Any]:
        """Add new user."""
        from bot.config import config
        
        # Determine user role, status, and permissions
        if user_id == config.owner_id:
            role = "owner"
            status = "active"
            permissions = "Full access"
        elif user_id in self.db_admins or user_id in config.admin_ids:
            role = "admin"
            status = "active"
            permissions = "Admin access"
        else:
            role = "member"
            status = "active"
            permissions = "Normal permissions only"
            
        user_data = {
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "role": role,
            "status": status,
            "permissions": permissions,
            "registered_at": datetime.utcnow().isoformat(),
            "last_active": datetime.utcnow().isoformat(),
            "total_checks": 0,
            "total_hits": 0,
            "total_dead": 0,
            "total_invalid": 0,
            "current_task_id": None
        }
        
        self.users[str(user_id)] = user_data
        await self._save_users()
        return user_data

    # Admin Management Methods
    async def add_admin(self, user_id: int) -> bool:
        """Add a user as admin."""
        if user_id not in self.db_admins:
            self.db_admins.append(user_id)
            await self._save_admins()
            
            # If user exists in database, update role and permissions
            user = await self.get_user(user_id)
            if user:
                user["role"] = "admin"
                user["permissions"] = "Admin access"
                await self._save_users()
            return True
        return False

    async def remove_admin(self, user_id: int) -> bool:
        """Remove a user from admins."""
        if user_id in self.db_admins:
            self.db_admins.remove(user_id)
            await self._save_admins()
            
            # If user exists in database, update role and permissions
            user = await self.get_user(user_id)
            if user:
                user["role"] = "member"
                user["permissions"] = "Normal permissions only"
                await self._save_users()
            return True
        return False

    async def get_admins(self) -> List[int]:
        """Get list of admin IDs."""
        return self.db_admins.copy()
    
    async def user_exists(self, user_id: int) -> bool:
        """Check if user exists."""
        return str(user_id) in self.users
    
    async def update_user_stats(self, user_id: int, stats: Dict[str, Any]):
        """Update user statistics."""
        user = await self.get_user(user_id)
        if user:
            user.update(stats)
            user["last_active"] = datetime.utcnow().isoformat()
            await self._save_users()
    
    async def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all registered users."""
        return list(self.users.values())
    
    async def get_users_count(self) -> int:
        """Get total users count."""
        return len(self.users)
    
    # Ban Methods
    async def ban_user(self, user_id: int):
        """Ban a user."""
        if user_id not in self.banned:
            self.banned.append(user_id)
            await self._save_banned()
    
    async def unban_user(self, user_id: int):
        """Unban a user."""
        if user_id in self.banned:
            self.banned.remove(user_id)
            await self._save_banned()
    
    async def is_banned(self, user_id: int) -> bool:
        """Check if user is banned."""
        return user_id in self.banned
    
    async def get_banned_users(self) -> List[int]:
        """Get list of banned users."""
        return self.banned.copy()
    
    # Task Methods
    async def create_task(self, user_id: int, task_id: str) -> Dict[str, Any]:
        """Create a new task."""
        task_data = {
            "task_id": task_id,
            "user_id": user_id,
            "status": "running",
            "created_at": datetime.utcnow().isoformat(),
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": None,
            "total_combos": 0,
            "processed": 0,
            "hits": 0,
            "dead": 0,
            "invalid": 0,
            "current_combo": "",
            "cancelled": False
        }
        
        self.tasks[task_id] = task_data
        
        # Update user's current task
        user = await self.get_user(user_id)
        if user:
            user["current_task_id"] = task_id
            await self._save_users()
        
        await self._save_tasks()
        return task_data
    
    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task by ID."""
        return self.tasks.get(task_id)
    
    async def update_task(self, task_id: str, updates: Dict[str, Any]):
        """Update task data."""
        task = await self.get_task(task_id)
        if task:
            task.update(updates)
            await self._save_tasks()
    
    async def cancel_task(self, task_id: str):
        """Cancel a task."""
        await self.update_task(task_id, {
            "status": "cancelled",
            "completed_at": datetime.utcnow().isoformat(),
            "cancelled": True
        })
        
        # Clear user's current task
        task = await self.get_task(task_id)
        if task:
            user = await self.get_user(task["user_id"])
            if user:
                user["current_task_id"] = None
                await self._save_users()
    
    async def complete_task(self, task_id: str):
        """Mark task as completed."""
        await self.update_task(task_id, {
            "status": "completed",
            "completed_at": datetime.utcnow().isoformat()
        })
        
        # Clear user's current task
        task = await self.get_task(task_id)
        if task:
            user = await self.get_user(task["user_id"])
            if user:
                user["current_task_id"] = None
                await self._save_users()
    
    async def get_active_tasks(self) -> List[Dict[str, Any]]:
        """Get all active tasks."""
        return [task for task in self.tasks.values() if task["status"] == "running"]
    
    async def get_user_active_task(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user's active task."""
        user = await self.get_user(user_id)
        if user and user["current_task_id"]:
            return await self.get_task(user["current_task_id"])
        return None
    
    async def get_task_history(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get task history."""
        tasks = list(self.tasks.values())
        if user_id:
            tasks = [t for t in tasks if t["user_id"] == user_id]
        return sorted(tasks, key=lambda x: x["created_at"], reverse=True)


# Global database instance
db = JsonDatabase()