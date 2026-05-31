import asyncio
import logging
import os
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.enums import ChatType
from aiogram.utils.keyboard import InlineKeyboardBuilder

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN не установлен!")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher()

BINANCE_API = "https://api.binance.com/api/v3/ticker/price?symbol="

# =====================================================

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

# =====================================================

async def get_prices(coin: str):
    coin = coin.upper()

    pairs = {
        "USDT": f"{coin}USDT",
        "RUB": f"{coin}RUB",
        "BTC": f"{coin}BTC",
        "ETH": f"{coin}ETH",
    }

    results = {}

    for name, pair in pairs.items():
        price = await fetch_price(pair)
        if price:
            results[name] = price

    return results

# =====================================================

async def format_message(coin: str):
    prices = await get_prices(coin)

    if not prices:
        return f"❌ Пара для <b>{coin}</b> не найдена на Binance.", False

    text = f"📊 <b>{coin}</b> (Binance)\n\n"

    signs = {
        "USDT": "$",
        "RUB": "₽",
        "BTC": "BTC",
        "ETH": "ETH"
    }

    for cur, value in prices.items():
        text += f"💰 {cur}: <code>{value}</code> {signs.get(cur,'')}\n"

    return text, True

# =====================================================

def get_keyboard(coin: str):
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Обновить", callback_data=f"upd_{coin}")
    return builder.as_markup()

# ======================= КОМАНДЫ ======================

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(
        "💎 <b>Crypto Binance Bot</b>\n\n"
        "Использование:\n"
        "<code>/c BTC</code>\n"
        "<code>/c ETH</code>\n\n"
        "Можно использовать в группе ✅"
    )

@dp.message(Command("c"))
async def coin_handler(message: types.Message, command: CommandObject):
    if not command.args:
        await message.reply("Пример: <code>/c BTC</code>")
        return

    coin = command.args.strip().upper()

    text, success = await format_message(coin)

    if success:
        await message.reply(
            text,
            reply_markup=get_keyboard(coin)
        )
    else:
        await message.reply(text)

# =====================================================

@dp.callback_query(F.data.startswith("upd_"))
async def update_handler(callback: types.CallbackQuery):
    coin = callback.data.split("_")[1]

    text, success = await format_message(coin)

    if success:
        await callback.message.edit_text(
            text,
            reply_markup=get_keyboard(coin)
        )
        await callback.answer("✅ Обновлено")
    else:
        await callback.answer("Ошибка")

# =====================================================

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
