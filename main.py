import os
import time
import threading
import requests
from datetime import datetime
from telebot import TeleBot, types

# ENV variables
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ACCESS_PASSWORD = os.environ.get("ACCESS_PASSWORD")
bot = TeleBot(TELEGRAM_BOT_TOKEN)

authorized_users = set()
user_wallets = {}
wallet_start_times = {}  # مدت نگه‌داری برای هر کیف‌پول

# تابع دریافت پوزیشن از GMX
def get_gmx_positions(wallet_address):
    url = f"https://gmx-server-mainnet.pyth.network/api/tradingStats?account={wallet_address.lower()}"
    try:
        res = requests.get(url)
        data = res.json()

        if not data or "positions" not in data:
            return None

        positions = data["positions"]
        if len(positions) == 0:
            return None

        pos = positions[0]

        position_type = pos.get("side", "Unknown")
        leverage = pos.get("leverage", 1)
        entry = float(pos.get("entryPriceUsd", 0))
        exit_price = float(pos.get("markPriceUsd", 0))
        profit_pct = pos.get("unrealizedPnlPercentage", 0)
        asset = pos.get("indexTokenSymbol", "Unknown")
        is_open = pos.get("isOpen", False)

        return {
            "platform": "GMX",
            "position": position_type,
            "entry": entry,
            "exit": exit_price,
            "profit_pct": profit_pct,
            "leverage": leverage,
            "asset": asset.upper(),
            "status": "باز" if is_open else "بسته"
        }

    except Exception as e:
        print("GMX API Error:", e)
        return None

# /start
@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.send_message(message.chat.id, "رمز عبور را وارد کنید:")

# ورود رمز
@bot.message_handler(func=lambda m: m.text == ACCESS_PASSWORD)
def grant_access(message):
    authorized_users.add(message.chat.id)
    bot.send_message(message.chat.id, "✅ دسترسی تأیید شد. از دستورات زیر استفاده کنید:\n/addwallet\n/listwallets\n/monitorwallet")

# عدم تایید رمز
@bot.message_handler(func=lambda m: m.text != ACCESS_PASSWORD and m.text.startswith("/") is False)
def deny_access(message):
    if message.chat.id not in authorized_users:
        bot.send_message(message.chat.id, "❌ رمز اشتباه است یا هنوز تأیید نشدید.")

# افزودن کیف پول
@bot.message_handler(commands=['addwallet'])
def add_wallet(message):
    if message.chat.id in authorized_users:
        msg = bot.send_message(message.chat.id, "🧾 لطفاً آدرس کیف پول را وارد کنید:")
        bot.register_next_step_handler(msg, save_wallet)

def save_wallet(message):
    wallet = message.text.strip()
    uid = message.chat.id
    user_wallets.setdefault(uid, []).append(wallet)
    wallet_start_times[wallet] = datetime.now()
    bot.send_message(uid, f"✅ کیف پول {wallet} ثبت شد.")

# لیست کیف‌پول‌ها
@bot.message_handler(commands=['listwallets'])
def list_wallets(message):
    uid = message.chat.id
    if uid in user_wallets:
        wallets = user_wallets[uid]
        response = "💼 کیف‌پول‌های ثبت‌شده:\n"
        for i, w in enumerate(wallets):
            response += f"{i+1}. {w}\n"
        bot.send_message(uid, response)
    else:
        bot.send_message(uid, "❌ هیچ کیف‌پولی ثبت نشده.")

# مانیتور کیف‌پول
@bot.message_handler(commands=['monitorwallet'])
def monitor_wallet(message):
    uid = message.chat.id
    if uid not in user_wallets:
        bot.send_message(uid, "🔑 لطفاً اول کیف‌پول اضافه کنید.")
        return

    bot.send_message(uid, "🔍 بررسی معاملات لحظه‌ای...")

    for wallet in user_wallets[uid]:
        bot.send_message(uid, f"📦 بررسی {wallet} ...")
        gmx_data = get_gmx_positions(wallet)

        if gmx_data:
            hold_time = datetime.now() - wallet_start_times.get(wallet, datetime.now())
            hours = int(hold_time.total_seconds() // 3600)
            profit_usd = round(gmx_data['entry'] * (gmx_data['profit_pct'] / 100), 2)
            asset_growth = 14.5  # عدد فرضی
            winrate = 87  # عدد فرضی

            msg = (
                "🎯 معاملات فیوچرز (Futures):\n"
                f"📍 Wallet: {wallet[:6]}...{wallet[-4:]}\n"
                f"📈 Position: {gmx_data['position']}  📊 Leverage: x{gmx_data['leverage']}\n"
                f"💰 Entry: ${gmx_data['entry']}  💸 Exit: ${gmx_data['exit']}\n"
                f"📈 Profit: {gmx_data['profit_pct']}٪  💵 سود دلاری: ${profit_usd}\n"
                f"🪙 Asset: Ethereum / {gmx_data['asset']}  🌐 Platform: GMX / GMX\n"
                f"📌 وضعیت معامله: {gmx_data['status']}\n"
                f"⏰ زمان نگهداری: {hours} ساعت\n"
                f"📈 رشد ارز: {asset_growth}٪  🎯 وین‌ریت: {winrate}٪"
            )
            bot.send_message(uid, msg)
        else:
            bot.send_message(uid, "⚠️ پوزیشنی برای این کیف‌پول یافت نشد.")

# اجرای ربات
bot.polling()
