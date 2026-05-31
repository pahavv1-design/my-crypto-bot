import asyncio
import logging
import os
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import ReplyKeyboardRemove, InlineQueryResultArticle, InputTextMessageContent
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.markdown import hbold

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN не установлен!")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher()

BINANCE_API = "https://api.binance.com/api/v3/ticker/24hr?symbol="

SUPPORTED_FIAT = ["USDT", "RUB", "EUR", "UAH", "KZT"]

# Автозамена тикеров
TICKER_FIX = {
    "TON": "TONCOIN"
}

# ================= BINANCE ===================

async def fetch_binance(symbol: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(BINANCE_API + symbol) as resp:
            if resp.status != 200:
                return None
            return await resp.json()

async def get_crypto_data(coin: str, currency: str = "USDT"):
    coin = coin.upper()
    coin = TICKER_FIX.get(coin, coin)

    pair = f"{coin}{currency}"

    data = await fetch_binance(pair)
    if not data:
        return None

    return {
        "price": float(data["lastPrice"]),
        "change": float(data["priceChangePercent"]),
        "volume": float(data["quoteVolume"])
    }

# ================= ЦБ РФ ===================

async def get_cbr():
    url = "https://www.cbr-xml-daily.ru/daily_json.js"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return None
            return await resp.json()

# ================= ФОРМАТ ===================

def format_crypto(coin, currency, data):
    sign = {
        "USDT": "$",
        "RUB": "₽",
        "EUR": "€",
        "UAH": "₴",
        "KZT": "₸"
    }.get(currency, "")

    arrow = "🟢" if data["change"] >= 0 else "🔴"

    text = (
        f"📊 <b>{coin}/{currency}</b>\n\n"
        f"💰 Цена: <code>{data['price']}</code> {sign}\n"
        f"{arrow} 24ч: <b>{data['change']}%</b>\n"
        f"📈 Объём: <code>{round(data['volume'],2)}</code>\n"
    )
    return text

# ================= КОМАНДЫ ===================

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "🚀 <b>CryptoLive24 PRO</b>\n\n"
        "/c BTC\n"
        "/c BTC RUB\n"
        "/c BTC ALL\n\n"
        "/usd\n"
        "/rates\n\n"
        "Inline режим:\n"
        "@CryptoLive24_bot BTC",
        reply_markup=ReplyKeyboardRemove()
    )

@dp.message(Command("usd"))
async def usd(message: types.Message):
    data = await get_cbr()
    if not data:
        await message.reply("Ошибка получения курса.")
        return

    usd = data["Valute"]["USD"]["Value"]
    await message.reply(f"💵 1 USD = <b>{round(usd,2)} ₽</b> (ЦБ РФ)")

@dp.message(Command("rates"))
async def rates(message: types.Message):
    data = await get_cbr()
    if not data:
        await message.reply("Ошибка получения данных.")
        return

    text = "💱 <b>Курсы ЦБ РФ</b>\n\n"
    for code in ["USD", "EUR", "CNY", "GBP"]:
        value = data["Valute"][code]["Value"]
        text += f"{code}: <b>{round(value,2)} ₽</b>\n"

    await message.reply(text)

@dp.message(Command("c"))
async def crypto(message: types.Message, command: CommandObject):
    if not command.args:
        await message.reply("Пример: /c BTC")
        return

    args = command.args.split()
    coin = args[0].upper()

    if len(args) > 1 and args[1].upper() == "ALL":
        text = ""
        for cur in SUPPORTED_FIAT:
            data = await get_crypto_data(coin, cur)
            if data:
                text += format_crypto(coin, cur, data) + "\n"
        if not text:
            await message.reply("Пара не найдена.")
            return
        await message.reply(text)
        return

    currency = args[1].upper() if len(args) > 1 else "USDT"

    data = await get_crypto_data(coin, currency)
    if not data:
        await message.reply("❌ Пара не найдена на Binance.")
        return

    await message.reply(format_crypto(coin, currency, data))

# ================= INLINE ===================

@dp.inline_query()
async def inline_handler(query: types.InlineQuery):
    text = query.query.upper()
    if not text:
        return

    data = await get_crypto_data(text, "USDT")
    if not data:
        return

    result = InlineQueryResultArticle(
        id="1",
        title=f"{text} цена",
        description=f"{data['price']} $",
        input_message_content=InputTextMessageContent(
            message_text=format_crypto(text, "USDT", data)
        )
    )

    await query.answer([result], cache_time=5)

# ================= ЗАПУСК ===================

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
