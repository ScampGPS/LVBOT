#!/usr/bin/env python3
"""
Clear any webhooks set for the bot to ensure polling works correctly
"""
import pathlib
from pathlib import Path
import sys

ROOT_DIR = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


import asyncio
import os
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

async def clear_webhook():
    """Clear webhook and get bot info"""
    bot = Bot(token=BOT_TOKEN)
    
    # Get current webhook info
    webhook_info = await bot.get_webhook_info()
    print(f"Current webhook URL: {webhook_info.url}")
    print(f"Has custom certificate: {webhook_info.has_custom_certificate}")
    print(f"Pending update count: {webhook_info.pending_update_count}")
    
    if webhook_info.url:
        print("\nWebhook is set! Clearing it...")
        result = await bot.delete_webhook(drop_pending_updates=True)
        print(f"Webhook cleared: {result}")
    else:
        print("\nNo webhook is set - bot is ready for polling")
    
    # Get bot info
    me = await bot.get_me()
    print(f"\nBot info:")
    print(f"Username: @{me.username}")
    print(f"Name: {me.first_name}")
    print(f"ID: {me.id}")

if __name__ == "__main__":
    asyncio.run(clear_webhook())
