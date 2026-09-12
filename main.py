import logging
import os
import ccxt
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get secrets
TOKEN = os.getenv("BOT_TOKEN")
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")

if not TOKEN:
    raise ValueError("BOT_TOKEN is missing")

# Bot memory
bot_state = {
    "auto_trading": False,
    "mode": "Paper Trading",
    "watchlist": ["BTC", "ETH", "SOL"],
    "risk_percent": 1.0,
    "confidence_threshold": 70
}

# Connect to Bybit
exchange = None
try:
    exchange = ccxt.bybit({
        "apiKey": BYBIT_API_KEY,
        "secret": BYBIT_API_SECRET,
        "enableRateLimit": True,
        "options": {
            "defaultType": "spot"
        }
    })
    # Load all markets so symbols work correctly
    exchange.load_markets()
    logger.info("Connected to Bybit and markets loaded")
except Exception as e:
    logger.error(f"Failed to connect to Bybit: {e}")
    exchange = None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Hello {user.first_name}!\n\n"
        "I am your Spot Trading Bot (Stage 3).\n\n"
        "Mode: Paper Trading (safe)\n\n"
        "Commands:\n"
        "/start - This message\n"
        "/status - Bot status\n"
        "/auto on|off - Turn auto trading on/off\n"
        "/pairs - Show watchlist\n"
        "/price BTC - Get current price"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    auto_status = "ON ✅" if bot_state["auto_trading"] else "OFF ❌"
    connection = "Connected ✅" if exchange else "Not connected ❌"

    message = (
        "📊 Bot Status\n\n"
        f"• Mode: {bot_state['mode']}\n"
        f"• Auto-trading: {auto_status}\n"
        f"• Bybit connection: {connection}\n"
        f"• Watchlist: {', '.join(bot_state['watchlist'])}\n"
        f"• Risk per trade: {bot_state['risk_percent']}%\n"
        f"• Confidence threshold: {bot_state['confidence_threshold']}\n"
        f"• Open positions: 0\n\n"
        "Still in Paper Trading. No real money is used."
    )
    await update.message.reply_text(message)


async def auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        current = "ON" if bot_state["auto_trading"] else "OFF"
        await update.message.reply_text(
            f"Auto-trading is currently {current}.\n\n"
            "Use:\n/auto on\n/auto off"
        )
        return

    command = context.args[0].lower()

    if command == "on":
        bot_state["auto_trading"] = True
        await update.message.reply_text("🤖 Auto-trading is now ON.\n(Paper Trading mode)")
    elif command == "off":
        bot_state["auto_trading"] = False
        await update.message.reply_text("🤖 Auto-trading is now OFF.")
    else:
        await update.message.reply_text("Please use /auto on or /auto off")


async def pairs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    watchlist = ", ".join(bot_state["watchlist"])
    await update.message.reply_text(f"Current watchlist:\n{watchlist}")


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get current price of a coin"""
    if not context.args:
        await update.message.reply_text("Please use like this:\n/price BTC")
        return

    if not exchange:
        await update.message.reply_text("Bybit is not connected.")
        return

    coin = context.args[0].upper()
    symbol = f"{coin}/USDT"

    try:
        ticker = exchange.fetch_ticker(symbol)
        last_price = ticker.get("last")

        if last_price is None:
            await update.message.reply_text(f"Could not find price for {symbol}")
            return

        await update.message.reply_text(
            f"💰 Current price of {symbol}:\n\n"
            f"${last_price}"
        )
    except Exception as e:
        # Show the real error so we can fix it
        error_message = str(e)
        logger.error(f"Price error: {error_message}")
        await update.message.reply_text(
            f"Error getting price for {symbol}:\n\n"
            f"{error_message}"
        )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception: {context.error}")


def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("auto", auto))
    application.add_handler(CommandHandler("pairs", pairs))
    application.add_handler(CommandHandler("price", price))

    application.add_error_handler(error_handler)

    logger.info("Bot starting (Stage 3 fixed)...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
