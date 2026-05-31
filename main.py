import asyncio
import logging
import os
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandObject
from aiogram.types import InlineQueryResultArticle, InputTextMessageContent
from aiogram.types import ReplyKeyboardRemove

TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher()

BINANCE_PRICE = "https://api.binance.com/api/v3/ticker/price?symbol="
BINANCE_24H = "https://api.binance.com/api/v3/ticker/24hr?symbol="
CBR_API = "https://www.cbr-xml-daily.ru/daily_json.js"


# ================= BINANCE =================

async def get_binance_price(pair):
    async with aiohttp.ClientSession() as session:
        async with session.get(BINANCE_PRICE + pair) as resp:
            if resp.status != 200:
                return None
            return float((await resp.json())["price"])


async def get_binance_24h(pair):
    async with aiohttp.ClientSession() as session:
        async with session.get(BINANCE_24H + pair) as resp:
            if resp.status != 200:
                return None
            return await resp.json()


# ================= ЦБ РФ =================

async def get_usd_rub():
    async with aiohttp.ClientSession() as session:
        async with session.get(CBR_API) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            return float(data["Valute"]["USD"]["Value"])


# ================= CRYPTO =================

async def build_crypto_message(coin: str):
    coin = coin.upper()

    pair = f"{coin}USDT"

    data = await get_binance_24h(pair)
    if not data:
        return None

    price_usdt = float(data["lastPrice"])
    change = float(data["priceChangePercent"])
    volume = float(data["quoteVolume"])

    usd_rub = await get_usd_rub()
    price_rub = price_usdt * usd_rub if usd_rub else None

    arrow = "🟢" if change >= 0 else "🔴"

    text = f"📊 <b>{coin}/USDT</b>\n\n"
    text += f"💵 USD: <b>{round(price_usdt,2)} $</b>\n"

    if price_rub:
        text += f"💰 RUB: <b>{round(price_rub,2)} ₽</b>\n"

    text += f"{arrow} 24ч: <b>{change}%</b>\n"
    text += f"📈 Объём: <code>{round(volume,2)}</code>\n"

    return text


# ================= КОМАНДЫ =================

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "🚀 <b>CryptoLive24 PRO</b>\n\n"
        "/c BTC\n"
        "/usd\n\n"
        "Inline:\n"
        "@CryptoLive24_bot BTC",
        reply_markup=ReplyKeyboardRemove()
    )


@dp.message(Command("usd"))
async def usd(message: types.Message):
    rate = await get_usd_rub()
    if not rate:
        await message.reply("Ошибка получения курса.")
        return

    await message.reply(f"💵 1 USD = <b>{round(rate,2)} ₽</b> (ЦБ РФ)")


@dp.message(Command("c"))
async def crypto(message: types.Message, command: CommandObject):
    if not command.args:
        await message.reply("Пример: /c BTC")
        return

    coin = command.args.strip().upper()
    text = await build_crypto_message(coin)

    if not text:
        await message.reply("❌ Монета не найдена на Binance.")
        return

    await message.reply(text)


# ================= INLINE =================

@dp.inline_query()
async def inline_handler(query: types.InlineQuery):
    coin = query.query.strip().upper()
    if not coin:
        return

    text = await build_crypto_message(coin)
    if not text:
        return

    result = InlineQueryResultArticle(
        id="1",
        title=f"{coin} цена",
        description="Актуальный курс",
        input_message_content=InputTextMessageContent(
            message_text=text
        )
    )

    await query.answer([result], cache_time=5)


# ================= ЗАПУСК =================

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
