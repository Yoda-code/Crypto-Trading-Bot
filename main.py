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

# Paper trading state
bot_state = {
    "auto_trading": False,
    "mode": "Paper Trading",
    "watchlist": ["BTC", "ETH", "SOL"],
    "risk_percent": 1.0,
    "confidence_threshold": 70,
    "balance": 10000.0,          # Starting fake money
    "positions": {}               # Example: {"BTC": {"amount": 0.01, "entry_price": 60000}}
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


def get_price(coin: str):
    """Get current price from CoinGecko"""
    coin = coin.upper()
    if coin not in COIN_IDS:
        return None

    coin_id = COIN_IDS[coin]
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        return data[coin_id]["usd"]
    except Exception as e:
        logger.error(f"Price error: {e}")
        return None


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
        return None, str(e)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Hello {user.first_name}!\n\n"
        "Spot Trading Bot – Paper Trading Mode\n\n"
        "Main commands:\n"
        "/status\n"
        "/buy BTC 500\n"
        "/close BTC\n"
        "/close BTC 50%\n"
        "/auto on|off\n"
        "/pairs\n"
        "/risk 1\n"
        "/threshold 70\n"
        "/price BTC\n"
        "/score BTC"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    auto_status = "ON ✅" if bot_state["auto_trading"] else "OFF ❌"
    balance = bot_state["balance"]
    positions = bot_state["positions"]

    message = (
        "📊 Paper Trading Portfolio\n\n"
        f"• Mode: {bot_state['mode']}\n"
        f"• Auto-trading: {auto_status}\n"
        f"• Balance: ${balance:,.2f}\n"
        f"• Risk per trade: {bot_state['risk_percent']}%\n"
        f"• Threshold: {bot_state['confidence_threshold']}\n"
        f"• Watchlist: {', '.join(bot_state['watchlist'])}\n\n"
    )

    if not positions:
        message += "Open positions: None"
    else:
        message += "Open positions:\n"
        total_value = 0
        for coin, pos in positions.items():
            current_price = get_price(coin)
            if current_price:
                value = pos["amount"] * current_price
                pnl = (current_price - pos["entry_price"]) * pos["amount"]
                pnl_pct = ((current_price - pos["entry_price"]) / pos["entry_price"]) * 100
                total_value += value
                message += (
                    f"\n{coin}:\n"
                    f"  Amount: {pos['amount']:.6f}\n"
                    f"  Entry: ${pos['entry_price']:,.2f}\n"
                    f"  Current: ${current_price:,.2f}\n"
                    f"  Value: ${value:,.2f}\n"
                    f"  PnL: ${pnl:,.2f} ({pnl_pct:+.2f}%)\n"
                )
            else:
                message += f"\n{coin}: (price unavailable)\n"

        message += f"\nTotal positions value: ${total_value:,.2f}"

    await update.message.reply_text(message)


async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Example:\n/buy BTC 500\n(This buys $500 worth of BTC)")
        return

    coin = context.args[0].upper()
    try:
        usdt_amount = float(context.args[1])
    except ValueError:
        await update.message.reply_text("Please enter a valid amount.\nExample: /buy BTC 500")
        return

    if coin not in COIN_IDS:
        await update.message.reply_text(f"{coin} is not supported yet.")
        return

    if usdt_amount <= 0:
        await update.message.reply_text("Amount must be greater than 0.")
        return

    if usdt_amount > bot_state["balance"]:
        await update.message.reply_text(
            f"Not enough balance.\nYou only have ${bot_state['balance']:,.2f}"
        )
        return

    price = get_price(coin)
    if price is None:
        await update.message.reply_text("Could not get current price. Try again.")
        return

    amount = usdt_amount / price

    # Update balance and position
    bot_state["balance"] -= usdt_amount

    if coin in bot_state["positions"]:
        # Average the entry price
        old = bot_state["positions"][coin]
        total_amount = old["amount"] + amount
        avg_price = ((old["amount"] * old["entry_price"]) + (amount * price)) / total_amount
        bot_state["positions"][coin] = {"amount": total_amount, "entry_price": avg_price}
    else:
        bot_state["positions"][coin] = {"amount": amount, "entry_price": price}

    await update.message.reply_text(
        f"✅ Paper Buy executed\n\n"
        f"Bought {amount:.6f} {coin}\n"
        f"Price: ${price:,.2f}\n"
        f"Cost: ${usdt_amount:,.2f}\n"
        f"Remaining balance: ${bot_state['balance']:,.2f}"
    )


async def close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Examples:\n"
            "/close BTC\n"
            "/close BTC 50%"
        )
        return

    coin = context.args[0].upper()

    if coin not in bot_state["positions"]:
        await update.message.reply_text(f"You have no open position for {coin}.")
        return

    pos = bot_state["positions"][coin]
    price = get_price(coin)
    if price is None:
        await update.message.reply_text("Could not get current price. Try again.")
        return

    # Check if user wants partial close
    close_percent = 100
    if len(context.args) > 1:
        arg = context.args[1].replace("%", "")
        try:
            close_percent = float(arg)
            if close_percent <= 0 or close_percent > 100:
                await update.message.reply_text("Percent must be between 1 and 100.")
                return
        except ValueError:
            await update.message.reply_text("Invalid percent. Example: /close BTC 50%")
            return

    close_amount = pos["amount"] * (close_percent / 100)
    usdt_received = close_amount * price
    pnl = (price - pos["entry_price"]) * close_amount

    # Update position and balance
    bot_state["balance"] += usdt_received

    if close_percent >= 100:
        del bot_state["positions"][coin]
    else:
        bot_state["positions"][coin]["amount"] -= close_amount

    await update.message.reply_text(
        f"✅ Paper Close executed\n\n"
        f"Closed {close_amount:.6f} {coin} ({close_percent}%)\n"
        f"Exit price: ${price:,.2f}\n"
        f"Received: ${usdt_received:,.2f}\n"
        f"PnL: ${pnl:,.2f}\n"
        f"New balance: ${bot_state['balance']:,.2f}"
    )


async def auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        current = "ON" if bot_state["auto_trading"] else "OFF"
        await update.message.reply_text(f"Auto-trading is currently {current}.\n\nUse:\n/auto on\n/auto off")
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
        await update.message.reply_text(
            f"Current watchlist:\n{', '.join(bot_state['watchlist'])}\n\n"
            "To change: /pairs BTC,ETH,SOL"
        )
        return

    raw = " ".join(context.args).replace(" ", ",").replace(";", ",")
    coins = [c.strip().upper() for c in raw.split(",") if c.strip()]

    valid = [c for c in coins if c in COIN_IDS]
    if not valid:
        await update.message.reply_text("No supported coins found.")
        return

    bot_state["watchlist"] = valid
    await update.message.reply_text(f"✅ Watchlist updated:\n{', '.join(valid)}")


async def risk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(f"Current risk: {bot_state['risk_percent']}%\n\nExample: /risk 1")
        return
    try:
        value = float(context.args[0].replace("%", ""))
        if 0.1 <= value <= 10:
            bot_state["risk_percent"] = value
            await update.message.reply_text(f"✅ Risk updated to {value}%")
        else:
            await update.message.reply_text("Risk must be between 0.1 and 10.")
    except ValueError:
        await update.message.reply_text("Example: /risk 1")


async def threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(f"Current threshold: {bot_state['confidence_threshold']}\n\nExample: /threshold 70")
        return
    try:
        value = int(context.args[0])
        if 50 <= value <= 95:
            bot_state["confidence_threshold"] = value
            await update.message.reply_text(f"✅ Threshold updated to {value}")
        else:
            await update.message.reply_text("Threshold must be between 50 and 95.")
    except ValueError:
        await update.message.reply_text("Example: /threshold 70")


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Example: /price BTC")
        return
    coin = context.args[0].upper()
    p = get_price(coin)
    if p:
        await update.message.reply_text(f"💰 {coin}/USDT\n\nPrice: ${p:,.2f}")
    else:
        await update.message.reply_text("Could not get price.")


async def score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Example: /score BTC")
        return
    coin = context.args[0].upper()
    score_value, reason = get_simple_score(coin)
    if score_value is None:
        await update.message.reply_text(f"Error: {reason}")
        return

    decision = "✅ PASS" if score_value >= bot_state["confidence_threshold"] else "❌ FAIL"
    await update.message.reply_text(
        f"📈 {coin} Confidence Score\n\n"
        f"Score: {score_value}/100\n"
        f"Threshold: {bot_state['confidence_threshold']}\n"
        f"Decision: {decision}\n\n"
        f"Reason: {reason}"
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception: {context.error}")


def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("buy", buy))
    application.add_handler(CommandHandler("close", close))
    application.add_handler(CommandHandler("auto", auto))
    application.add_handler(CommandHandler("pairs", pairs))
    application.add_handler(CommandHandler("risk", risk))
    application.add_handler(CommandHandler("threshold", threshold))
    application.add_handler(CommandHandler("price", price))
    application.add_handler(CommandHandler("score", score))
    application.add_error_handler(error_handler)

    logger.info("Bot starting with Paper Trading...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
