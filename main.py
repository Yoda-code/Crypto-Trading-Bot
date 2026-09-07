import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Enable logging so we can see what the bot is doing
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get the bot token from environment variable (safe way)
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    logger.error("BOT_TOKEN is not set!")
    raise ValueError("BOT_TOKEN environment variable is missing")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_text(
        f"Hello {user.first_name}!\n\n"
        "I am your Trading Bot.\n"
        "Right now I am in Stage 1 (basic version).\n\n"
        "Available commands:\n"
        "/start - Show this message\n"
        "/status - Show current status\n"
        "/auto - Show auto-trading status"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show basic status."""
    await update.message.reply_text(
        "📊 Bot Status\n\n"
        "• Mode: Paper Trading (coming soon)\n"
        "• Auto-trading: Off\n"
        "• Exchange: Bybit (not connected yet)\n"
        "• Open positions: 0\n\n"
        "This is Stage 1. More features will be added step by step."
    )


async def auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show auto-trading status."""
    await update.message.reply_text(
        "🤖 Auto-trading is currently OFF.\n\n"
        "We will add the on/off switch in a later stage."
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Log errors."""
    logger.error(f"Exception while handling an update: {context.error}")


def main():
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("auto", auto))

    # Register error handler
    application.add_error_handler(error_handler)

    # Start the bot
    logger.info("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
