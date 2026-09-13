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


def get_simple_score(coin: str):
    coin = coin.upper()
    if coin not in COIN_IDS:
        return None, "Coin not supported yet"

    coin_id = COIN_IDS[coin]
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"

    try:
        response = requests.get(url, timeout=10)
        data = response.json()

        market_data = data.get("market_data", {})
        price_change_24h = market_data.get("price_change_percentage_24h", 0) or 0
        price_change_7d = market_data.get("price_change_percentage_7d", 0) or 0
        price_change_30d = market_data.get("price_change_percentage_30d", 0) or 0

        score = 50
        reasons = []

        if price_change_30d > 5:
            score += 20
            reasons.append("Positive 30-day trend (+20)")
        elif price_change_30d < -5:
            score -= 15
            reasons.append("Negative 30-day trend (-15)")

        if price_change_7d > 3:
            score += 15
            reasons.append("Good 7-day momentum (+15)")
        elif price_change_7d < -3:
            score -= 10
            reasons.append("Weak 7-day momentum (-10)")

        if price_change_24h > 2:
            score += 10
            reasons.append("Strong 24h move (+10)")
        elif price_change_24h < -2:
            score -= 10
            reasons.append("Weak 24h move (-10)")

        score = max(0, min(100, score))

        if not reasons:
            reasons.append("Neutral market conditions")

        return score, " | ".join(reasons)

    except Exception as e:
        logger.error(f"Score error: {e}")
        return None, str(e)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Hello {user.first_name}!\n\n"
        "Spot Trading Bot\n"
        "Mode: Paper Trading\n\n"
        "Commands:\n"
        "/start\n"
        "/status\n"
        "/auto on|off\n"
        "/pairs\n"
        "/pairs BTC,ETH,SOL\n"
        "/risk 1\n"
        "/threshold 70\n"
        "/price BTC\n"
        "/score BTC"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    auto_status = "ON ✅" if bot_state["auto_trading"] else "OFF ❌"

    message = (
        "📊 Bot Status\n\n"
        f"• Mode: {bot_state['mode']}\n"
        f"• Auto-trading: {auto_status}\n"
        f"• Price data: CoinGecko\n"
        f"• Watchlist: {', '.join(bot_state['watchlist'])}\n"
        f"• Risk per trade: {bot_state['risk_percent']}%\n"
        f"• Confidence threshold: {bot_state['confidence_threshold']}\n"
        f"• Open positions: 0\n\n"
        "Paper Trading – no real money used."
    )
    await update.message.reply_text(message)


async def auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        current = "ON" if bot_state["auto_trading"] else "OFF"
        await update.message.reply_text(
            f"Auto-trading is currently {current}.\n\nUse:\n/auto on\n/auto off"
        )
        return

    command = context.args[0].lower()
    if command == "on":
        bot_state["auto_trading"] = True
        await update.message.reply_text("🤖 Auto-trading is now ON (Paper mode)")
    elif command == "off":
        bot_state["auto_trading"] = False
        await update.message.reply_text("🤖 Auto-trading is now OFF")
    else:
        await update.message.reply_text("Use /auto on or /auto off")


async def pairs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        watchlist = ", ".join(bot_state["watchlist"])
        await update.message.reply_text(
            f"Current watchlist:\n{watchlist}\n\n"
            "To change it:\n/pairs BTC,ETH,SOL"
        )
        return

    raw = " ".join(context.args)
    raw = raw.replace(" ", ",").replace(";", ",")
    coins = [c.strip().upper() for c in raw.split(",") if c.strip()]

    if not coins:
        await update.message.reply_text("Example: /pairs BTC,ETH,SOL")
        return

    valid_coins = []
    invalid_coins = []

    for coin in coins:
        if coin in COIN_IDS:
            valid_coins.append(coin)
        else:
            invalid_coins.append(coin)

    if not valid_coins:
        await update.message.reply_text("No supported coins found.")
        return

    bot_state["watchlist"] = valid_coins

    message = f"✅ Watchlist updated!\n\nNew list:\n{', '.join(valid_coins)}"
    if invalid_coins:
        message += f"\n\nIgnored: {', '.join(invalid_coins)}"

    await update.message.reply_text(message)


async def risk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            f"Current risk per trade: {bot_state['risk_percent']}%\n\n"
            "To change it:\n/risk 1\n/risk 0.5"
        )
        return

    try:
        value = float(context.args[0].replace("%", ""))
        if value <= 0 or value > 10:
            await update.message.reply_text("Please choose a risk between 0.1 and 10.")
            return

        bot_state["risk_percent"] = value
        await update.message.reply_text(f"✅ Risk per trade updated to {value}%")
    except ValueError:
        await update.message.reply_text("Please enter a number.\nExample: /risk 1")


async def threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            f"Current confidence threshold: {bot_state['confidence_threshold']}\n\n"
            "To change it:\n/threshold 70\n/threshold 80"
        )
        return

    try:
        value = int(context.args[0])
        if value < 50 or value > 95:
            await update.message.reply_text("Please choose a threshold between 50 and 95.")
            return

        bot_state["confidence_threshold"] = value
        await update.message.reply_text(f"✅ Confidence threshold updated to {value}")
    except ValueError:
        await update.message.reply_text("Please enter a number.\nExample: /threshold 70")


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Example: /price BTC")
        return

    coin = context.args[0].upper()
    if coin not in COIN_IDS:
        await update.message.reply_text("Coin not supported yet.")
        return

    coin_id = COIN_IDS[coin]
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"

    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        price_value = data[coin_id]["usd"]
        await update.message.reply_text(f"💰 {coin}/USDT\n\nPrice: ${price_value}")
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")


async def score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Example: /score BTC")
        return

    coin = context.args[0].upper()
    score_value, reason = get_simple_score(coin)

    if score_value is None:
        await update.message.reply_text(f"Could not calculate score.\n{reason}")
        return

    if score_value >= bot_state["confidence_threshold"]:
        decision = "✅ PASS – would consider a trade"
    else:
        decision = "❌ FAIL – score too low"

    message = (
        f"📈 Confidence Score for {coin}\n\n"
        f"Score: {score_value}/100\n"
        f"Threshold: {bot_state['confidence_threshold']}\n"
        f"Decision: {decision}\n\n"
        f"Reason: {reason}"
    )
    await update.message.reply_text(message)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception: {context.error}")


def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("auto", auto))
    application.add_handler(CommandHandler("pairs", pairs))
    application.add_handler(CommandHandler("risk", risk))
    application.add_handler(CommandHandler("threshold", threshold))
    application.add_handler(CommandHandler("price", price))
    application.add_handler(CommandHandler("score", score))
    application.add_error_handler(error_handler)

    logger.info("Bot starting with risk & threshold commands...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
