import os
import time
import requests
import threading
from datetime import datetime, timedelta
from telebot import TeleBot

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ACCESS_PASSWORD = os.environ.get("ACCESS_PASSWORD")

bot = TeleBot(TELEGRAM_BOT_TOKEN)
authorized_users = set()
wallets = {}

# ————————————————————————————————————————
# 📦 GMX API واقعی
def get_gmx_positions(wallet):
    try:
        url = f"https://gmx-server-mainnet.pyth.network/api/tradingStats?account={wallet.lower()}"
        res = requests.get(url)
        data = res.json()
        if not data or "positions" not in data:
            return []
        positions = []
        for pos in data["positions"]:
            position = {
                "platform": "GMX",
                "platform_tag": "GMX",
                "position": pos.get("side", "Unknown"),
                "leverage": pos.get("leverage", 1),
                "entry": float(pos.get("entryPriceUsd", 0)),
                "exit": float(pos.get("markPriceUsd", 0)),
                "profit_pct": pos.get("unrealizedPnlPercentage", 0),
                "asset": pos.get("indexTokenSymbol", "Unknown").upper(),
                "asset_name": get_asset_name(pos.get("indexTokenSymbol", "Unknown").upper()),
                "status": "باز" if pos.get("isOpen", False) else "بسته",
                "time": "۲ ساعت پیش"  # فقط نمونه – باید واقعی بشه
            }
            positions.append(position)
        return positions
    except Exception as e:
        print("GMX Error:", e)
        return []

# ————————————————————————————————————————
# 📦 dYdX / GNS / Synthetix (داده فرضی تا اضافه کنیم)
def get_dydx_positions(wallet):
    return []

def get_gains_positions(wallet):
    return []

def get_synthetix_positions(wallet):
    return []

def get_asset_name(symbol):
    names = {
        "ETH": "Ethereum",
        "BTC": "Bitcoin",
        "ARB": "Arbitrum",
        "OP": "Optimism",
    }
    return names.get(symbol.upper(), symbol)

# ————————————————————————————————————————
# ✅ دستورات ربات
@bot.message_handler(commands=["start"])
def handle_start(msg):
    bot.send_message(msg.chat.id, "👋 لطفاً رمز عبور را وارد کنید:")

@bot.message_handler(func=lambda m: m.text == ACCESS_PASSWORD)
def handle_password(msg):
    authorized_users.add(msg.chat.id)
    bot.send_message(msg.chat.id, "✅ رمز صحیح بود!\nدستورات:\n/addwallet\n/listwallets\n/monitorwallet")

@bot.message_handler(commands=["addwallet"])
def handle_add_wallet(msg):
    if msg.chat.id not in authorized_users:
        return
    sent = bot.send_message(msg.chat.id, "📍 لطفاً آدرس کیف‌پول را وارد کنید:")
    bot.register_next_step_handler(sent, save_wallet)

def save_wallet(msg):
    if msg.chat.id not in wallets:
        wallets[msg.chat.id] = []
    wallets[msg.chat.id].append(msg.text.strip())
    bot.send_message(msg.chat.id, "✅ کیف‌پول ثبت شد!")

@bot.message_handler(commands=["listwallets"])
def handle_list_wallets(msg):
    ws = wallets.get(msg.chat.id, [])
    if not ws:
        bot.send_message(msg.chat.id, "❌ هیچ کیف‌پولی ثبت نشده.")
        return
    result = "\n".join([f"{i+1}. {w}" for i, w in enumerate(ws)])
    bot.send_message(msg.chat.id, f"📄 لیست کیف‌پول‌ها:\n{result}")

@bot.message_handler(commands=["monitorwallet"])
def handle_monitor(msg):
    uid = msg.chat.id
    if uid not in wallets or not wallets[uid]:
        bot.send_message(uid, "⚠️ اول کیف‌پول اضافه کنید.")
        return

    bot.send_message(uid, "📡 شروع مانیتور لحظه‌ای کیف‌پول‌ها...")

    def monitor():
        while True:
            for w in wallets[uid]:
                gmx_data = get_gmx_positions(w)
                for d in gmx_data:
                    text = (
                        f"🎯 معاملات فیوچرز (Futures):\n"
                        f"📍 Wallet: `{w[:6]}...{w[-4:]}`\n"
                        f"📈 Position: `{d['position']}` 📊 Leverage: `x{d['leverage']}`\n"
                        f"💰 Entry: `${d['entry']}` 💸 Exit: `${d['exit']}`\n"
                        f"📈 Profit: `{d['profit_pct']}٪` 🪙 Asset: `{d['asset_name']} / {d['asset']}`\n"
                        f"🌐 Platform: `{d['platform']} / {d['platform_tag']}`\n"
                        f"⏰ زمان معامله: `{d['time']}`\n"
                        f"🔄 وضعیت معامله: `{d['status']}`"
                    )
                    bot.send_message(uid, text, parse_mode="Markdown")
            time.sleep(60)

    threading.Thread(target=monitor).start()

# ————————————————————————————————————————
bot.polling()
