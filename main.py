import asyncio
import logging
import os
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.utils.keyboard import InlineKeyboardBuilder

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN не установлен!")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher()

BINANCE_API = "https://api.binance.com/api/v3/ticker/price?symbol="

SUPPORTED_FIAT = ["USD", "RUB", "EUR", "UAH", "KZT"]

# ===============================================
# Получение цены с Binance
# ===============================================

async def fetch_price(symbol: str):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(BINANCE_API + symbol) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                return float(data["price"])
        except:
            return None

# ===============================================
# Курс доллара ЦБ РФ
# ===============================================

async def get_usd_rate():
    url = "https://www.cbr-xml-daily.ru/daily_json.js"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            return data["Valute"]["USD"]["Value"]

# ===============================================
# Формирование ответа
# ===============================================

async def get_crypto_price(coin: str, currency: str = None):
    coin = coin.upper()

    results = {}

    if currency and currency != "ALL":
        currency = currency.upper()
        if currency not in SUPPORTED_FIAT:
            return None

        pair = f"{coin}{currency}"
        price = await fetch_price(pair)
        if price:
            results[currency] = price

    else:
        for cur in SUPPORTED_FIAT:
            pair = f"{coin}{cur}"
            price = await fetch_price(pair)
            if price:
                results[cur] = price

    return results if results else None

# ===============================================
# Кнопка
# ===============================================

def get_keyboard(coin: str, currency: str):
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🔄 Обновить",
        callback_data=f"upd_{coin}_{currency or 'ALL'}"
    )
    return builder.as_markup()

# ===============================================
# Команды
# ===============================================

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(
        "💎 <b>CryptoLive24</b>\n\n"
        "Примеры:\n"
        "<code>/c BTC</code>\n"
        "<code>/c BTC RUB</code>\n"
        "<code>/c ETH USD</code>\n"
        "<code>/c TON ALL</code>\n\n"
        "<code>/usd</code> — курс доллара ЦБ"
    )

@dp.message(Command("usd"))
async def usd_handler(message: types.Message):
    rate = await get_usd_rate()
    await message.reply(
        f"💵 <b>Курс доллара (ЦБ РФ)</b>\n\n"
        f"<code>1 USD = {round(rate,2)} ₽</code>"
    )

@dp.message(Command("c"))
async def crypto_handler(message: types.Message, command: CommandObject):
    if not command.args:
        await message.reply("Пример: <code>/c BTC</code>")
        return

    args = command.args.split()
    coin = args[0]
    currency = args[1] if len(args) > 1 else None

    prices = await get_crypto_price(coin, currency)

    if not prices:
        await message.reply("❌ Пара не найдена на Binance.")
        return

    text = f"📊 <b>{coin.upper()}</b> (Binance)\n\n"

    symbols = {
        "USD": "$",
        "RUB": "₽",
        "EUR": "€",
        "UAH": "₴",
        "KZT": "₸"
    }

    for cur, value in prices.items():
        text += f"💰 {cur}: <code>{value}</code> {symbols.get(cur,'')}\n"

    await message.reply(
        text,
        reply_markup=get_keyboard(coin.upper(), currency)
    )

# ===============================================
# Обновление
# ===============================================

@dp.callback_query(F.data.startswith("upd_"))
async def update_handler(callback: types.CallbackQuery):
    _, coin, currency = callback.data.split("_")

    currency = None if currency == "ALL" else currency

    prices = await get_crypto_price(coin, currency)

    if not prices:
        await callback.answer("Ошибка обновления")
        return

    text = f"📊 <b>{coin}</b> (Binance)\n\n"

    symbols = {
        "USD": "$",
        "RUB": "₽",
        "EUR": "€",
        "UAH": "₴",
        "KZT": "₸"
    }

    for cur, value in prices.items():
        text += f"💰 {cur}: <code>{value}</code> {symbols.get(cur,'')}\n"

    await callback.message.edit_text(
        text,
        reply_markup=get_keyboard(coin, currency)
    )

    await callback.answer("✅ Обновлено")

# ===============================================

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
