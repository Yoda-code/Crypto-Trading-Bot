import logging
import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN is missing")

bot_state = {
    "auto_trading": False,
    "mode": "Paper Trading",
    "watchlist": ["BTC", "ETH", "SOL"],
    "risk_percent": 1.0,
    "confidence_threshold": 70
}

# Simple mapping for CoinGecko
COIN_IDS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "AVAX": "avalanche-2",
    "DOT": "polkadot",
    "LINK": "chainlink"
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Hello {user.first_name}!\n\n"
        "Spot Trading Bot\n"
        "Mode: Paper Trading (safe)\n\n"
        "Commands:\n"
        "/start - Welcome message\n"
        "/status - Bot status\n"
        "/auto on|off - Turn auto-trading on or off\n"
        "/pairs - Show watchlist\n"
        "/price BTC - Get current price"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    auto_status = "ON ✅" if bot_state["auto_trading"] else "OFF ❌"

    message = (
        "📊 Bot Status\n\n"
        f"• Mode: {bot_state['mode']}\n"
        f"• Auto-trading: {auto_status}\n"
        f"• Price data: CoinGecko (public)\n"
        f"• Watchlist: {', '.join(bot_state['watchlist'])}\n"
        f"• Risk per trade: {bot_state['risk_percent']}%\n"
        f"• Confidence threshold: {bot_state['confidence_threshold']}\n"
        f"• Open positions: 0\n\n"
        "Paper Trading mode – no real money is used."
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
        await update.message.reply_text("🤖 Auto-trading is now ON\n(Paper Trading mode)")
    elif command == "off":
        bot_state["auto_trading"] = False
        await update.message.reply_text("🤖 Auto-trading is now OFF")
    else:
        await update.message.reply_text("Please use /auto on or /auto off")


async def pairs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    watchlist = ", ".join(bot_state["watchlist"])
    await update.message.reply_text(f"Current watchlist:\n{watchlist}")


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Example:\n/price BTC")
        return

    coin = context.args[0].upper()

    if coin not in COIN_IDS:
        await update.message.reply_text(
            f"Sorry, I don't have {coin} in my list yet.\n"
            "Try: BTC, ETH, SOL, BNB, XRP, ADA, DOGE"
        )
        return

    coin_id = COIN_IDS[coin]
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"

    try:
        response = requests.get(url, timeout=10)
        data = response.json()

        if coin_id in data and "usd" in data[coin_id]:
            price = data[coin_id]["usd"]
            await update.message.reply_text(
                f"💰 {coin}/USDT\n\n"
                f"Price: ${price}"
            )
        else:
            await update.message.reply_text(f"Could not find price for {coin}")
    except Exception as e:
        await update.message.reply_text(
            f"Sorry, could not get the price.\nError: {str(e)}"
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

    logger.info("Bot starting with CoinGecko prices...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
