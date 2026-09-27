import os
import asyncio
import logging
import yfinance as yf
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
bot_state = {"is_active": False}
logging.basicConfig(level=logging.INFO)

def calculate_trade_levels(price, action):
    atr = price * 0.0050
    if action == "BUY":
        sl = round(price - (atr * 1.5), 4)
        tp1 = round(price + (atr * 1.5), 4)
        tp2 = round(price + (atr * 3.0), 4)
    else:
        sl = round(price + (atr * 1.5), 4)
        tp1 = round(price - (atr * 1.5), 4)
        tp2 = round(price - (atr * 3.0), 4)
    return sl, tp1, tp2

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏛 Bot Ready!\n/engine_on - চালু\n/engine_off - বন্ধ")

async def engine_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    bot_state["is_active"] = True
    await update.message.reply_text("🟢 SYSTEM ONLINE")

async def engine_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    bot_state["is_active"] = False
    await update.message.reply_text("🔴 SYSTEM OFFLINE")

async def algo_signal_engine(app):
    pairs = {"XAUUSD=X": "GOLD", "EURUSD=X": "EUR/USD", "BTC-USD": "BTC/USD"}
    while True:
        if bot_state["is_active"]:
            for symbol, name in pairs.items():
                try:
                    data = yf.download(tickers=symbol, period="5d", interval="15m", progress=False)
                    if len(data) < 200: continue
                    close = data['Close'].squeeze()
                    price = float(close.iloc[-1])
                    rsi = float(RSIIndicator(close=close, window=14).rsi().iloc[-1])
                    ema = float(EMAIndicator(close=close, window=200).ema_indicator().iloc[-1])
                    action = None
                    if rsi <= 32 and price > ema*0.98: action = "BUY"
                    elif rsi >= 68 and price < ema*1.02: action = "SELL"
                    if action:
                        sl, tp1, tp2 = calculate_trade_levels(price, action)
                        card = f"🏛 SIGNAL: {name}\n{action}\nEntry: {price}\nTP1: {tp1}\nTP2: {tp2}\nSL: {sl}"
                        await app.bot.send_message(chat_id=ADMIN_ID, text=card)
                        await asyncio.sleep(300)
                except Exception as e:
                    logging.error(e)
        await asyncio.sleep(120)

async def post_init(application):
    asyncio.create_task(algo_signal_engine(application))

if __name__ == '__main
