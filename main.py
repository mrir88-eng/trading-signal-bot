import os, asyncio, logging, threading
from datetime import datetime
import yfinance as yf
from flask import Flask
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.environ.get("TELEGRAM_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
bot_state = {"is_active": False}
last_prices = {}

logging.basicConfig(level=logging.WARNING)
web_app = Flask(__name__)
@web_app.route('/')
def home(): return "V14 ALL-IN-ONE LIVE - 7 Features Active"
def run_web(): web_app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
threading.Thread(target=run_web, daemon=True).start()

async def start(update, context):
    txt = "🤖 **V14 ALL-IN-ONE READY**\n\n7 টা সুবিধা একসাথে:\n1. Rate Alert\n2. 70-100% Confidence\n3. RSI+EMA Filter\n4. News Filter\n5. 3TP + BE\n6. Auto Update\n7. Dashboard\n\n/engine_on - চালু\n/engine_off - বন্ধ"
    await update.message.reply_text(txt, parse_mode='Markdown')

async def engine_on(update, context):
    if update.effective_user.id!= ADMIN_ID: return
    bot_state["is_active"] = True
    await update.message.reply_text("🟢 **V14 ONLINE - ALL 7 SYSTEMS ACTIVE**", parse_mode='Markdown')

async def engine_off(update, context):
    if update.effective_user.id!= ADMIN_ID: return
    bot_state["is_active"] = False
    await update.message.reply_text("🔴 OFFLINE")

async def upgrade_engine(app):
    pairs = {"XAUUSD=X": "GOLD", "BTC-USD": "BTC", "EURUSD=X": "EURUSD"}
    while True:
        if not bot_state["is_active"]:
            await asyncio.sleep(5); continue

        now_utc = datetime.utcnow()
        is_news_time = now_utc.hour in [13, 14, 15] and now_utc.weekday() < 5

        header = f"⚠️ NEWS FILTER - Signal Paused (Price Live)\n" if is_news_time else f"📈 **LIVE UPDATE {now_utc.strftime('%H:%M')} UTC**\n"
        status_text = header + "Bot: 🟢 ONLINE | 7 Features: ON\n\n"

        signal_found = None
        for symbol, name in pairs.items():
            try:
                data = yf.download(symbol, period="5d", interval="5m", progress=False)
                if len(data) < 200: continue
                close = data['Close'].squeeze()
                price = float(close.iloc[-1])
                rsi = float(RSIIndicator(close=close).rsi().iloc[-1])
                ema = float(EMAIndicator(close=close, window=200).ema_indicator().iloc[-1])

                # 1. RATE ALERT
                rate_text = ""
                if name in last_prices:
                    diff = ((price - last_prices[name]) / last_prices[name]) * 100
                    if abs(diff) >= 0.15 and not is_news_time:
                        emoji = "🚀 PUMP" if diff > 0 else "📉 DUMP"
                        await app.bot.send_message(chat_id=ADMIN_ID, text=f"⚡️ **RATE ALERT**\n{name} {emoji} {diff:+.2f}%\nPrice: {price:.2f}")
                    rate_text = f"{diff:+.2f}%"
                last_prices[name] = price
                status_text += f"{name}: ${price:.2f} ({rate_text}) | RSI {rsi:.0f}\n"

                if is_news_time: continue

                # 2 & 3. CONFIDENCE + FILTER
                action = None; conf = 0
                if rsi <= 32 and price > ema:
                    action = "BUY"; conf = 70 + (32 - rsi) * 2.5
                elif rsi >= 68 and price < ema:
                    action = "SELL"; conf = 70 + (rsi - 68) * 2.5
                if conf > 100: conf = 100

                if action and conf >= 70 and not signal_found:
                    signal_found = (name, action, price, rsi, conf)
            except: pass

        # 5. 3TP SIGNAL
        if signal_found:
            name, action, price, rsi, conf = signal_found
            if action == "BUY":
                sl = price - 10; tp1 = price + 7; tp2 = price + 15; tp3 = price + 28
            else:
                sl = price + 10; tp1 = price - 7; tp2 = price - 15; tp3 = price - 28

            msg = (f"🔥 **V14 MONSTER ({conf:.0f}%)** 🔥\n\n"
                   f"Pair: {name}\nAction: **{action}**\nPrice: {price:.2f}\n\n"
                   f"🛑 SL: {sl:.2f}\n"
                   f"✅ TP1: {tp1:.2f} (50% Close + BE)\n"
                   f"✅ TP2: {tp2:.2f} (30% Close)\n"
                   f"✅ TP3: {tp3:.2f} (20% Runner)\n\n"
                   f"⚠️ **Note:** TP1 হিট করলে SL Entry তে আনবে")
            await app.bot.send_message(chat_id=ADMIN_ID, text=msg, parse_mode='Markdown')
            await asyncio.sleep(900)
        else:
            # 6. AUTO UPDATE
            await app.bot.send_message(chat_id=ADMIN_ID, text=status_text, parse_mode='Markdown')

        await asyncio.sleep(900) # 15 min

async def post_init(app):
    asyncio.create_task(upgrade_engine(app))

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('engine_on', engine_on))
    app.add_handler(CommandHandler('engine_off', engine_off))
    app.run_polling()
