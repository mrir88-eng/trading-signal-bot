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

def calculate_trade_levels(price, action, rsi, ema_200):
    atr = price * 0.0050
    if action == "BUY":
        sl = round(price - (atr * 1.5), 4)
        tp1 = round(price + (atr * 1.5), 4)
        tp2 = round(price + (atr * 3.0), 4)
    else:
        sl = round(price + (atr * 1.5), 4)
        tp1 = round(price - (atr * 1.5), 4)
        tp2 = round(price - (atr * 3.0), 4)
    
    score = 70
    if (action == "BUY" and price > ema_200) or (action == "SELL" and price < ema_200):
        score += 20
    if (action == "BUY" and rsi < 40) or (action == "SELL" and rsi > 60):
        score += 10
    return sl, tp1, tp2, min(score, 98)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "🏛 **PRO-TRADER ALGO v3.0**\n\n/engine_on - Bot চালু\n/engine_off - Bot বন্ধ\n/system_status - স্ট্যাটাস"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def engine_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    bot_state["is_active"] = True
    await update.message.reply_text("🟢 **SYSTEM ONLINE**")

async def engine_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    bot_state["is_active"] = False
    await update.message.reply_text("🔴 **SYSTEM OFFLINE**")

async def system_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = "🟢 RUNNING" if bot_state["is_active"] else "🔴 STANDBY"
    await update.message.reply_text(f"Core Engine: {s}", parse_mode="Markdown")

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
                        sl, tp1, tp2, score = calculate_trade_levels(price, action, rsi, ema)
                        icon = "🟢 BUY" if action == "BUY" else "🔴 SELL"
                        card = (f"🏛 **SIGNAL ALERT**\n━━━━━━━━━━━━\nAsset: {name}\nOrder: {icon}\nEntry: {price}\n\nTP1: {tp1}\nTP2: {tp2}\nSL: {sl}\n━━━━━━━━━━━━\nScore: {score}% | RSI: {round(rsi,2)}")
                        kb = [[InlineKeyboardButton("📈 Trade Now", url="https://www.exness.com/")]]
                        await app.bot.send_message(chat_id=ADMIN_ID, text=card, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
                        await
