# Seedr Bot Setup Guide

This guide will walk you through the complete process of setting up and running the Seedr Combo Checker Bot from scratch on either Windows or Linux.

## Prerequisites
Before you begin, ensure you have the following installed on your system:
- **Python 3.8+** (Download from [python.org](https://www.python.org/downloads/))
- **Git** (Download from [git-scm.com](https://git-scm.com/downloads))

---

## Step 1: Uploading to GitHub & Ignoring `.env`

If you are uploading this project to your own GitHub repository, make sure you **DO NOT upload your `.env` file**. The `.env` file contains sensitive information like your bot token and admin IDs.

1. Ensure there is a `.gitignore` file in your main directory.
2. The `.gitignore` file should contain at least these lines:
   ```text
   .env
   __pycache__/
   venv/
   data/
   temp/
   logs/
   *.txt
   ```
3. Commit and push your files to GitHub. Your `.env` will be ignored automatically if it's in the `.gitignore`.

---

## Step 2: Cloning the Repository

On the machine where you want to run the bot (your PC, a VPS, etc.), open your terminal or command prompt.

Clone your repository using Git:
```bash
git clone https://github.com/yourusername/your-repo-name.git
cd your-repo-name
```
*(Replace the URL with your actual GitHub repository URL).*

---

## Step 3: Setting Up the Virtual Environment (Optional but Recommended)

It's best practice to use a virtual environment so the bot's dependencies don't interfere with your system's Python packages.

**For Windows:**
```powershell
python -m venv venv
venv\Scripts\activate
```

**For Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

---

## Step 4: Installing Requirements

Once you are inside the directory (and your virtual environment is activated), install the required Python packages.

**For Windows:**
```powershell
pip install -r requirements.txt
```

**For Linux / macOS:**
```bash
pip3 install -r requirements.txt
```

---

## Step 5: Configuring the `.env` File

Since the `.env` file was ignored during the GitHub upload, you need to create it manually on the machine running the bot.

You can create and edit the `.env` file directly from the terminal.

**For Linux / macOS:**
```bash
# Create and open the file in the nano editor
nano .env
```
*(Once in `nano`, paste the configuration below, then press `Ctrl+O`, `Enter`, and `Ctrl+X` to save and exit).*

**For Windows:**
```powershell
# Create and open the file in Notepad
notepad .env
```
*(Notepad will ask if you want to create a new file. Click Yes, paste the configuration, save it, and close the window).*

Copy the following structure into your new `.env` file:

```env
# Telegram Bot Configuration
BOT_TOKEN=your_bot_token_here
OWNER_ID=your_telegram_id_here
ADMIN_IDS=another_admin_id,yet_another_id

# Rate Limits & Settings
MAX_CONCURRENT_TASKS=1
CHECKER_THREADS=20
```

**Update the values**:
- `BOT_TOKEN`: Get this from [@BotFather](https://t.me/BotFather) on Telegram.
- `OWNER_ID`: Your personal Telegram User ID (Get this from a bot like @userinfobot).
- `ADMIN_IDS`: (Optional) Comma-separated list of other admin user IDs.

---

## Step 6: Running the Bot

Now that everything is set up, you can start the bot.

**For Windows:**
```powershell
python main.py
```

**For Linux / macOS:**
```bash
python3 main.py
```

You should see logs in the terminal indicating that the bot has started successfully, loaded the database, and passed its health checks. You can now go to Telegram and send `/start` to your bot.

---

## Additional Commands for Linux/VPS Users (Background Running)

If you are running this on a Linux server and want the bot to keep running after you close the terminal, you can use `tmux` or `screen`.

Using `tmux`:
```bash
# Create a new session
tmux new -s seedr_bot

# Run the bot
python3 main.py

# Detach from session: Press Ctrl+B, then press D
# To re-attach later:
tmux attach -t seedr_bot
```
