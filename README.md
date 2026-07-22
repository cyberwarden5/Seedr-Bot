# Telegram Combo Checker Bot

A premium, production-ready Telegram bot for authorized credential verification (supporting Seedr.cc account checks).

## ⚠️ IMPORTANT NOTICE

This bot is designed **ONLY** for verifying credentials that the operator is authorized to test:
- Accounts you personally own
- Accounts where you have explicit written permission to test
- Authorized security testing with proper documentation

**DO NOT** use this bot for unauthorized access to accounts, credential stuffing, or any illegal activities.

## Key Features

- ✅ **Single Combo Checking (`/chk <email:pass>`)**: Validate credentials instantly.
- ✅ **Bulk File Checking (`/txt`)**: Upload `.txt` combo lists for concurrent checking.
- ✅ **Group Chat Support**: Upload files directly with the `/txt` caption, or reply to files in group chats.
- ✅ **Role-Based Concurrency**: Dynamic multithreading settings based on user roles (Owner, Admin, Member).
- ✅ **Member Cooldown Timeout**: Restrict members from abusing resources via configurable cooldown limits.
- ✅ **Live Dashboard CPM Metrics**: Real-time progress tracker with Elapsed Time, Remaining Time, and CPM Speed (without emoji clutter).
- ✅ **Task Cancellation**: Cancel running tasks instantly via command (`/cancel`) or inline callback buttons (mapped by `task_id`).
- ✅ **Log Channel Reporting**: Automatic forwarding of registration, startup stats, task execution tracking, and premium hit notifications to your log channel.
- ✅ **Admin Controls & Stats**: Manage administrators, view checking stats, and ban/unban users.

## Quick Start

### Prerequisites

- Python 3.12+
- Telegram Bot Token (from @BotFather)
- Telegram Channel ID (for bot logging and premium hit notifications)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd combo-checker-bot
```

2. Create a virtual environment and install dependencies:
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

3. Create your `.env` file from the configuration structure below and run:
```bash
python main.py
```