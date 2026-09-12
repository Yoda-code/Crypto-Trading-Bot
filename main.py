import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get the bot token safely
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    logger.error("BOT_TOKEN is not set!")
    raise ValueError("BOT_TOKEN environment variable is missing")

# Simple memory for the bot (will improve later)
bot_state = {
    "auto_trading": False,
    "mode": "Paper Trading",
    "watchlist": ["BTC", "ETH", "SOL"],
    "risk_percent": 1.0,
    "confidence_threshold": 70
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message"""
    user = update.effective_user
    await update.message.reply_text(
        f"Hello {user.first_name}!\n\n"
        "I am your Spot Trading Bot (Stage 2).\n\n"
        "Current mode: Paper Trading (fake money)\n\n"
        "Available commands:\n"
        "/start - Show this message\n"
        "/status - Show bot status\n"
        "/auto on - Turn auto-trading ON\n"
        "/auto off - Turn auto-trading OFF\n"
        "/pairs - Show current watchlist"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current status"""
    auto_status = "ON ✅" if bot_state["auto_trading"] else "OFF ❌"

    message = (
        "📊 Bot Status\n\n"
        f"• Mode: {bot_state['mode']}\n"
        f"• Auto-trading: {auto_status}\n"
        f"• Exchange: Bybit (not connected yet)\n"
        f"• Watchlist: {', '.join(bot_state['watchlist'])}\n"
        f"• Risk per trade: {bot_state['risk_percent']}%\n"
        f"• Confidence threshold: {bot_state['confidence_threshold']}\n"
        f"• Open positions: 0\n\n"
        "Still in Paper Trading. No real money is used."
    )
    await update.message.reply_text(message)


async def auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Turn auto-trading on or off"""
    if not context.args:
        current = "ON" if bot_state["auto_trading"] else "OFF"
        await update.message.reply_text(
            f"Auto-trading is currently {current}.\n\n"
            "Use:\n"
            "/auto on\n"
            "/auto off"
        )
        return

    command = context.args[0].lower()

    if command == "on":
        bot_state["auto_trading"] = True
        await update.message.reply_text("🤖 Auto-trading is now ON.\n\n(Still Paper Trading mode)")
        logger.info("Auto-trading turned ON")
    elif command == "off":
        bot_state["auto_trading"] = False
        await update.message.reply_text("🤖 Auto-trading is now OFF.")
        logger.info("Auto-trading turned OFF")
    else:
        await update.message.reply_text("Please use /auto on or /auto off")


async def pairs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the current watchlist"""
    watchlist = ", ".join(bot_state["watchlist"])
    await update.message.reply_text(
        f"Current watchlist:\n{watchlist}\n\n"
        "We will add the ability to change it in the next stage."
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Log the error and send a telegram message to notify the developer."""
    logger.error(f"Exception while handling an update: {context.error}")


def main():
    """Start the bot"""
    application = Application.builder().token(TOKEN).build()

    # Commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("auto", auto))
    application.add_handler(CommandHandler("pairs", pairs))

    # Error handler
    application.add_error_handler(error_handler)

    logger.info("Bot is starting (Stage 2)...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
