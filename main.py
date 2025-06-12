import os
import time
import threading
import requests
from telebot import TeleBot, types
from datetime import datetime, timedelta

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ACCESS_PASSWORD = os.environ.get("ACCESS_PASSWORD")
BSCSCAN_API_KEY = os.environ.get("BSCSCAN_API_KEY")

bot = TeleBot(TELEGRAM_BOT_TOKEN)

authorized_users = set()
user_wallets = {}

def relative_time(timestamp):
    now = datetime.utcnow()
    dt = datetime.utcfromtimestamp(timestamp)
    diff = now - dt
    if diff.days >= 1:
        return f"{diff.days} روز پیش"
    hours = diff.seconds // 3600
    if hours >= 1:
        return f"{hours} ساعت پیش"
    minutes = (diff.seconds % 3600) // 60
    return f"{minutes} دقیقه پیش"

def fake_transactions(wallet):
    # شبیه‌سازی داده‌های اسپات و فیوچرز برای تست
    now = datetime.utcnow().timestamp()
    return {
        "spot": [
            {
                "symbol": "ETH",
                "full_name": "Ethereum",
                "amount": 250.23,
                "timestamp": now - 3600,  # 1 ساعت پیش
                "price": 2800,
                "growth": 14.5,
            }
        ],
        "futures": [
            {
                "symbol": "ETH",
                "full_name": "Ethereum",
                "entry": 2500,
                "exit": 2780,
                "profit_pct": 11.2,
                "position": "Long",
                "leverage": "x10",
                "timestamp": now - 3000,  # 50 دقیقه پیش
                "platform": "GMX",
                "platform_tag": "GMX"
            }
        ]
    }

def calculate_win_rate(wallet):
    return 87  # مقدار ساختگی برای تست

@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.send_message(message.chat.id, "رمز عبور را وارد کنید:")

@bot.message_handler(func=lambda m: m.text == ACCESS_PASSWORD)
def grant_access(message):
    authorized_users.add(message.chat.id)
    bot.send_message(message.chat.id, "✅ دسترسی تأیید شد.\n\nدستورات ربات:\n/addwallet\n/listwallets\n/monitorwallet\n/activity")

@bot.message_handler(func=lambda m: m.text != ACCESS_PASSWORD and m.text.startswith("/") is False)
def deny_access(message):
    if message.chat.id not in authorized_users:
        bot.send_message(message.chat.id, "❌ رمز عبور اشتباه است یا هنوز تأیید نشده‌اید.")

@bot.message_handler(commands=['addwallet'])
def add_wallet(message):
    if message.chat.id in authorized_users:
        msg = bot.send_message(message.chat.id, "لطفاً آدرس کیف‌پول را وارد کنید:")
        bot.register_next_step_handler(msg, save_wallet)

def save_wallet(message):
    wallet = message.text.strip()
    uid = message.chat.id
    if uid not in user_wallets:
        user_wallets[uid] = []
    user_wallets[uid].append(wallet)
    bot.send_message(uid, f"✅ کیف‌پول {wallet} ثبت شد.")

@bot.message_handler(commands=['listwallets'])
def list_wallets(message):
    uid = message.chat.id
    if uid in user_wallets and user_wallets[uid]:
        response = "📋 لیست کیف‌پول‌های ثبت‌شده:\n"
        for i, w in enumerate(user_wallets[uid]):
            response += f"{i+1}. {w}\n"
        bot.send_message(uid, response)
    else:
        bot.send_message(uid, "⚠️ هیچ کیف‌پولی ثبت نشده است.")

@bot.message_handler(commands=['monitorwallet'])
def monitor_wallet(message):
    uid = message.chat.id
    if uid not in user_wallets or not user_wallets[uid]:
        bot.send_message(uid, "⚠️ لطفاً اول کیف‌پول ثبت کنید با /addwallet")
        return

    for wallet in user_wallets[uid]:
        tx = fake_transactions(wallet)

        now = datetime.utcnow().timestamp()
        recent_spot = [t for t in tx["spot"] if now - t["timestamp"] <= 172800]
        recent_futures = [t for t in tx["futures"] if now - t["timestamp"] <= 172800]

        if not recent_spot and not recent_futures:
            bot.send_message(uid, f"🔍 این کیف‌پول در حال حاضر معامله‌ای نداشته است.\nآیا مایلید تراکنش‌های قدیمی آن را ببینید؟ (پاسخ بده: بله)")
            return

        if recent_spot:
            bot.send_message(uid, f"📦 معاملات اسپات (Spot):")
            for tx in recent_spot:
                msg = (
                    f"📍 کیف‌پول:        `{wallet[:6]}...{wallet[-4:]}`\n"
                    f"🪙 ارز:            `{tx['full_name']} / {tx['symbol']}`      ⏰ زمان: `{relative_time(tx['timestamp'])}`\n"
                    f"📦 مقدار:          `{tx['amount']}`       💵 قیمت خرید: `${tx['price']}`\n"
                    f"📈 رشد ارز:        `{tx['growth']}٪`\n"
                )
                bot.send_message(uid, msg, parse_mode="Markdown")

        if recent_futures:
            bot.send_message(uid, f"🎯 معاملات فیوچرز (Futures):")
            for tx in recent_futures:
                msg = (
                    f"📍 Wallet:           `{wallet[:6]}...{wallet[-4:]}`\n"
                    f"📈 Position:         `{tx['position']}`       📊 Leverage: `{tx['leverage']}`\n"
                    f"💰 Entry:            `${tx['entry']}`        💸 Exit:     `${tx['exit']}`\n"
                    f"📈 Profit:           `{tx['profit_pct']}٪`     🪙 Asset:    `{tx['full_name']} / {tx['symbol']}`\n"
                    f"🌐 Platform:         `{tx['platform']} / {tx['platform_tag']}`\n"
                    f"⏰ زمان معامله:     `{relative_time(tx['timestamp'])}`\n"
                )
                bot.send_message(uid, msg, parse_mode="Markdown")

        # وین‌ریت
        win_rate = calculate_win_rate(wallet)
        bot.send_message(uid, f"🎯 وین‌ریت کیف‌پول `{wallet[:6]}...{wallet[-4:]}` برابر است با: `{win_rate}%`", parse_mode="Markdown")

@bot.message_handler(commands=['activity'])
def check_activity(message):
    uid = message.chat.id
    if uid not in user_wallets or not user_wallets[uid]:
        bot.send_message(uid, "⚠️ لطفاً کیف‌پولی ثبت کنید.")
        return
    bot.send_message(uid, "📊 بررسی خریدهای اخیر در حال انجام است...")
    for wallet in user_wallets[uid]:
        bot.send_message(uid, f"✅ بررسی آدرس: {wallet} => خریدی انجام شده است.")

bot.polling()
