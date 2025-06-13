import os
import time
import threading
import requests
from telebot import TeleBot, types

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ACCESS_PASSWORD = os.environ.get("ACCESS_PASSWORD")

bot = TeleBot(TELEGRAM_BOT_TOKEN)
authorized_users = set()
user_wallets = {}

# ----------------- GMX -----------------
def get_gmx_positions(wallet_address):
    url = f"https://gmx-server-mainnet.pyth.network/api/tradingStats?account={wallet_address.lower()}"
    try:
        res = requests.get(url)
        data = res.json()
        if not data or "positions" not in data:
            return None
        pos = data["positions"][0]
        return {
            "platform": "GMX",
            "position": pos.get("side", "Unknown"),
            "entry": float(pos.get("entryPriceUsd", 0)),
            "exit": float(pos.get("markPriceUsd", 0)),
            "profit_pct": pos.get("unrealizedPnlPercentage", 0),
            "leverage": pos.get("leverage", 1),
            "asset": pos.get("indexTokenSymbol", "Unknown").upper(),
            "status": "باز" if pos.get("isOpen", False) else "بسته"
        }
    except:
        return None

# ----------------- dYdX -----------------
def get_dydx_positions(wallet_address):
    url = f"https://api.dydx.exchange/v3/accounts/{wallet_address}"
    try:
        res = requests.get(url)
        data = res.json()
        if "account" not in data:
            return None
        pos = data["account"]
        return {
            "platform": "dYdX",
            "position": pos.get("positionId", "Unknown"),
            "entry": float(pos.get("openVolumeUsd", 0)),
            "exit": float(pos.get("equityUsd", 0)),
            "profit_usd": float(pos.get("totalPnlUsd", 0)),
            "leverage": pos.get("leverage", 1),
            "asset": pos.get("quoteAsset", "USD").upper(),
            "status": "باز" if pos.get("openVolumeUsd", 0) > 0 else "بسته"
        }
    except:
        return None

# ----------------- Gains -----------------
def get_gains_positions(wallet_address):
    url = f"https://api.gains.trade/api/positions?address={wallet_address.lower()}"
    try:
        res = requests.get(url)
        data = res.json()
        if not data:
            return None
        pos = data[0]
        return {
            "platform": "Gains",
            "position": pos.get("direction", "Unknown"),
            "entry": float(pos.get("entryPrice", 0)),
            "exit": float(pos.get("currentPrice", 0)),
            "profit_pct": float(pos.get("pnlPercent", 0)),
            "leverage": float(pos.get("leverage", 1)),
            "asset": pos.get("pair", "Unknown").upper(),
            "status": "باز" if pos.get("isOpen", True) else "بسته"
        }
    except:
        return None

# ----------------- Synthetix -----------------
def get_synthetix_positions(wallet_address):
    url = f"https://api.synthetix.io/positions/{wallet_address.lower()}"
    try:
        res = requests.get(url)
        data = res.json()
        if "positions" not in data:
            return None
        pos = data["positions"][0]
        return {
            "platform": "Synthetix",
            "position": pos.get("positionType", "Unknown"),
            "entry": float(pos.get("entryPrice", 0)),
            "exit": float(pos.get("currentPrice", 0)),
            "profit_pct": float(pos.get("pnlPercent", 0)),
            "leverage": float(pos.get("leverage", 1)),
            "asset": pos.get("asset", "Unknown").upper(),
            "status": "باز" if pos.get("open", True) else "بسته"
        }
    except:
        return None

# ----------------- Bot Commands -----------------

@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.send_message(message.chat.id, "سلام! لطفاً رمز عبور را وارد کنید:")

@bot.message_handler(func=lambda m: m.text == ACCESS_PASSWORD)
def grant_access(message):
    authorized_users.add(message.chat.id)
    bot.send_message(message.chat.id, "دسترسی تأیید شد ✅\nدستورات:\n/addwallet\n/listwallets\n/monitorwallet")

@bot.message_handler(commands=['addwallet'])
def add_wallet(message):
    if message.chat.id in authorized_users:
        msg = bot.send_message(message.chat.id, "آدرس کیف پول را وارد کن:")
        bot.register_next_step_handler(msg, save_wallet)

def save_wallet(message):
    uid = message.chat.id
    wallet = message.text.strip()
    user_wallets.setdefault(uid, []).append(wallet)
    bot.send_message(uid, f"کیف پول {wallet} ذخیره شد.")

@bot.message_handler(commands=['listwallets'])
def list_wallets(message):
    uid = message.chat.id
    wallets = user_wallets.get(uid, [])
    if not wallets:
        bot.send_message(uid, "هیچ کیف پولی ثبت نشده.")
    else:
        msg = "📋 کیف‌پول‌های شما:\n" + "\n".join(wallets)
        bot.send_message(uid, msg)

@bot.message_handler(commands=['monitorwallet'])
def monitor_wallet(message):
    uid = message.chat.id
    if uid not in authorized_users or uid not in user_wallets:
        bot.send_message(uid, "اول رمز را وارد و کیف‌پول ثبت کن.")
        return
    bot.send_message(uid, "شروع مانیتورینگ کیف‌پول‌ها...")

    def monitor():
        while True:
            for wallet in user_wallets[uid]:
                text = f"📍 کیف‌پول: `{wallet[:6]}...{wallet[-4:]}`\n"
                for func in [get_gmx_positions, get_dydx_positions, get_gains_positions, get_synthetix_positions]:
                    result = func(wallet)
                    if result:
                        text += f"""
🌐 {result['platform']}:
📈 Position: {result['position']}  📊 Leverage: x{result['leverage']}
💰 Entry: ${result['entry']}       💸 Exit: ${result['exit']}
📈 Profit: {result['profit_pct']}% 🪙 Asset: {result['asset']}
📌 Status: {result['status']}\n"""
                bot.send_message(uid, text, parse_mode="Markdown")
            time.sleep(60)

    threading.Thread(target=monitor).start()

bot.polling()
