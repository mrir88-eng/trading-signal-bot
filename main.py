import os
import asyncio
import logging
import yfinance as yf
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# এনভায়রনমেন্ট কনফিগারেশন
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

# সিস্টেম গ্লোবাল স্টেট
bot_state = {
    "is_active": False,
    "last_signal_time": {},
    "risk_per_trade": 1.0  # ডিফল্ট ঝুঁকি: ১%
}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ------------------- প্রফেশনাল ট্রেডিং ম্যাথ -------------------
def calculate_trade_levels(price, action, rsi, ema_200):
    """টেকনিক্যাল সূচকের ওপর ভিত্তি করে ডায়নামিক TP/SL এবং কনফ্লুয়েন্স স্কোর নির্ধারণ"""
    atr_estimate = price * 0.0050  # আনুমানিক মার্কেট ভোলাটিলিটি buffer
    
    if action == "BUY":
        sl = round(price - (atr_estimate * 1.5), 2 if price > 50 else 4)
        tp1 = round(price + (atr_estimate * 1.5), 2 if price > 50 else 4)
        tp2 = round(price + (atr_estimate * 3.0), 2 if price > 50 else 4)
    else: # SELL
        sl = round(price + (atr_estimate * 1.5), 2 if price > 50 else 4)
        tp1 = round(price - (atr_estimate * 1.5), 2 if price > 50 else 4)
        tp2 = round(price - (atr_estimate * 3.0), 2 if price > 50 else 4)
        
    # কনফ্লুয়েন্স স্কোর (ট্রেডের শক্তিমত্তা)
    score = 70
    if (action == "BUY" and price > ema_200) or (action == "SELL" and price < ema_200):
        score += 20  # ট্রেন্ডের দিকে ট্রেড
    if (action == "BUY" and rsi < 40) or (action == "SELL" and rsi > 60):
        score += 10  # প্রাতিষ্ঠানিক লিকুইডিটি এন্ট্রি
        
    return sl, tp1, tp2, min(score, 98)

# ------------------- কমান্ড হ্যান্ডলারসমূহ -------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_msg = (
        "🏛 **PRO-TRADER ALGO SIGNAL SYSTEM v3.0**\n"
        "━━━━━ Institutional Control Panel ━━━━━\n\n"
        "হাই-টেক অ্যানালিটিক্স এবং ট্রেন্ড অ্যালগরিদম ভিত্তিক সিগন্যাল সেশন।\n\n"
        "⚡ **অ্যাডমিন কমান্ডস:**\n"
        "• `/engine_on` - প্রফেশনাল অটো-অ্যানালাইসিস চালু\n"
        "• `/engine_off` - অ্যালগরিদম পজ করা\n"
        "• `/system_status` - লাইভ সার্ভার ও ট্রেন্ড স্ট্যাটাস"
    )
    await update.message.reply_text(welcome_msg, parse_mode="Markdown")

async def engine_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ **Access Denied:** Unauthorized Admin Attempt.")
        return

    if bot_state["is_active"]:
        await update.message.reply_text("⚠️ **Notice:** Algorithm engine is already active and scanning.")
    else:
        bot_state["is_active"] = True
        await update.message.reply_text("🟢 **SYSTEM ONLINE:** Live Technical Analysis Engine Activated.")

async def engine_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ **Access Denied:** Unauthorized Admin Attempt.")
        return

    bot_state["is_active"] = False
    await update.message.reply_text("🔴 **SYSTEM OFFLINE:** Live Signal Engine Suspended.")

async def system_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_str = "🟢 RUNNING (ACTIVE)" if bot_state["is_active"] else "🔴 STANDBY (OFF)"
    status_card = (
        f"🖥 **SYSTEM DIAGNOSTICS**\n"
        f"━━━━━ Server & Core Status ━━━━━\n"
        f"▪ **Core Engine:** `{status_str}`\n"
        f"▪ **Scanning Assets:** `XAU/USD, EUR/USD, BTC/USD`\n"
        f"▪ **Timeframe:** `15m Multi-Confluence`\n"
        f"▪ **Execution Speed:** `Instant (Auto-Routing)`"
    )
    await update.message.reply_text(status_card, parse_mode="Markdown")

# ------------------- প্রফেশনাল অটোমেটেড অ্যানালাইসিস ইঞ্জিন -------------------
async def algo_signal_engine(app):
    pairs = {
        "XAUUSD=X": "GOLD (XAU/USD)",
        "EURUSD=X": "EUR/USD",
        "BTC-USD": "BITCOIN (BTC/USD)"
    }
    
    while True:
        if bot_state["is_active"]:
            for symbol, display_name in pairs.items():
                try:
                    # মার্কেট ডেটা ফেচ (১৫ মিনিটের ক্যান্ডেল)
                    data = yf.download(tickers=symbol, period="5d", interval="15m", progress=False)
                    if data.empty or len(data) < 200:
                        continue

                    close = data['Close'].squeeze()
                    current_price = float(close.iloc[-1])

                    # টেকনিক্যাল ইন্ডিকেটর গণনা (RSI + 200 EMA)
                    rsi_val = float(RSIIndicator(close=close, window=14).rsi().iloc[-1])
                    ema_200 = float(EMAIndicator(close=close, window=200).ema_indicator().iloc[-1])

                    action = None
                    # ওভারসোল্ড অ্যালগরিদম কন্ডিশন (Buy Signal)
                    if rsi_val <= 32 and current_price > (ema_200 * 0.98):
                        action = "BUY"
                    # ওভারবট অ্যালগরিদম কন্ডিশন (Sell Signal)
                    elif rsi_val >= 68 and current_price < (ema_200 * 1.02):
                        action = "SELL"

                    if action:
                        sl, tp1, tp2, score = calculate_trade_levels(current_price, action, rsi_val, ema_200)
                        
                        action_icon = "🟢 INSTANT BUY" if action == "BUY" else "🔴 INSTANT SELL"
                        
                        # হাই-টেক টেলিগ্রাম লেআউট
                        signal_card = (
                            f"🏛 **INSTITUTIONAL SIGNAL ALERT** 🏛\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"🔤 **Asset:** `{display_name}`\n"
                            f"⚡ **Order Type:** *{action_icon}*\n"
                            f"📍 **Entry Zone:** `{round(current_price, 2 if current_price > 50 else 4)}`\n\n"
                            f"🎯 **Target 1 (TP1):** `{tp1}`\n"
                            f"🎯 **Target 2 (TP2):** `{tp2}`\n"
                            f"🛑 **Stop Loss (SL):** `{sl}`\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"📊 **Confluence Score:** `{score}% Confidence`\n"
                            f"📈 **RSI (14):** `{round(rsi_val, 2)}` | **EMA 200:** `{round(ema_200, 2)}`\n"
                            f"🛡 **Risk Management:** `1% - 2% Max Per Trade`\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━"
                        )
                        
                        # প্রফেশনাল ডায়নামিক বাটন
                        keyboard = [
                            [
                                InlineKeyboardButton("📈 Open Chart / Trade", url="https://www.exness.com/"),
                                InlineKeyboardButton("📊 Risk Calculator", url="https://www.myfxbook.com/forex-calculators/position-size")
                            ]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)

                        await app.bot.send_message(
                            chat_id=ADMIN_ID,
                            text=signal_card,
                            parse_mode="Markdown",
                            reply_markup=reply_markup
                        )
                        # ডুপ্লিকেট সিগন্যাল এড়াতে ১০ মিনিট বিরতি
                        await asyncio.sleep(600)

                except Exception as e:
                    logging.error(f"Error executing engine for {symbol}: {e}")

        # প্রসেসর কুলডাউন (প্রতি ২ মিনিট পর চেক করবে)
        await asyncio.sleep(120)

# ------------------- মূল অ্যাপ্লিকেশন রানিং পয়েন্ট -------------------
if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # কমান্ড সেটআপ
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('engine_on', engine_on))
    app.add_handler(CommandHandler('engine_off', engine_off))
    app.add_handler(CommandHandler('system_status', system_status))

    # ব্যাকগ্রাউন্ড টাস্ক ইনিশিয়ালাইজেশন
    loop = asyncio.get_event_loop() if hasattr(asyncio, "get_event_loop") else asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(algo_signal_engine(app))

    print("High-Tech Trading Signal Engine Online...")
    app.run_polling()
