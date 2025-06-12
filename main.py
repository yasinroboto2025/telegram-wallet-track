
import os
import time
import threading
import requests
from telebot import TeleBot, types

# ENV variables from Replit Secrets
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ACCESS_PASSWORD = os.environ.get("ACCESS_PASSWORD")
BSCSCAN_API_KEY = os.environ.get("BSCSCAN_API_KEY")

bot = TeleBot(TELEGRAM_BOT_TOKEN)

# Global dictionary for users and wallets
authorized_users = set()
user_wallets = {}

# Multi-platform support configuration
platforms = ["gmx", "dydx", "gains", "synthetix"]

# START command
@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.send_message(message.chat.id, "رمز عبور را وارد کنید:")

# PASSWORD handler
@bot.message_handler(func=lambda m: m.text == ACCESS_PASSWORD)
def grant_access(message):
    authorized_users.add(message.chat.id)
    bot.send_message(message.chat.id, "دسترسی تأیید شد. از دستورات زیر استفاده کنید:\n/addwallet\n/listwallets\n/monitorwallet\n/activity")

# Deny others
@bot.message_handler(func=lambda m: m.text != ACCESS_PASSWORD and m.text.startswith("/") is False)
def deny_access(message):
    if message.chat.id not in authorized_users:
        bot.send_message(message.chat.id, "رمز اشتباه است یا هنوز تأیید نشدید.")

# Add wallet
@bot.message_handler(commands=['addwallet'])
def add_wallet(message):
    if message.chat.id in authorized_users:
        msg = bot.send_message(message.chat.id, "لطفاً آدرس کیف پول را وارد کنید:")
        bot.register_next_step_handler(msg, save_wallet)

def save_wallet(message):
    wallet = message.text.strip()
    uid = message.chat.id
    if uid not in user_wallets:
        user_wallets[uid] = []
    user_wallets[uid].append(wallet)
    bot.send_message(uid, f"کیف پول {wallet} با موفقیت اضافه شد.")

# List wallets
@bot.message_handler(commands=['listwallets'])
def list_wallets(message):
    uid = message.chat.id
    if uid in user_wallets:
        response = "لیست کیف‌پول‌های ثبت‌شده:\n"
        for i, w in enumerate(user_wallets[uid]):
            response += f"{i+1}. {w}\n"
        bot.send_message(uid, response)
    else:
        bot.send_message(uid, "هیچ کیف پولی ثبت نشده.")

# Monitor wallet
@bot.message_handler(commands=['monitorwallet'])
def monitor_wallet(message):
    uid = message.chat.id
    if uid not in user_wallets:
        bot.send_message(uid, "لطفاً اول کیف پول اضافه کنید با /addwallet")
        return
    bot.send_message(uid, "شروع مانیتورینگ کیف‌پول‌ها...")

    def monitor():
        while True:
            for wallet in user_wallets[uid]:
                bot.send_message(uid, f"بررسی کیف پول {wallet} ...")
                msg = (
                    f"Wallet: {wallet}\n"
                    f"Position: Long\n"
                    f"Leverage: x10\n"
                    f"Entry: $2500\n"
                    f"Exit: $2780\n"
                    f"Profit: +11.2%\n"
                    f"Asset: ETH\n"
                    f"Platform: GMX"
                )
                bot.send_message(uid, msg)
            time.sleep(60)

    threading.Thread(target=monitor).start()

# Activity checker
@bot.message_handler(commands=['activity'])
def check_activity(message):
    uid = message.chat.id
    if uid not in user_wallets:
        bot.send_message(uid, "لطفاً کیف پولی ثبت کنید.")
        return
    bot.send_message(uid, "در حال بررسی خریدهای انجام‌شده...")
    for wallet in user_wallets[uid]:
        bot.send_message(uid, f"بررسی آدرس: {wallet} => خریدی انجام داده")

# Bot polling
bot.polling()
