import asyncio
import logging
import os
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- НАСТРОЙКИ ---
TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

async def fetch_price(coin: str, vs_currency: str):
    """Получает цену монеты к RUB или USDT"""
    coin = coin.upper()
    symbol = f"{coin}{vs_currency}"
    url = f"https://api.bybit.com/v5/market/tickers?category=spot&symbol={symbol}"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=5) as resp:
                data = await resp.json()
                if data['retCode'] == 0 and data['result']['list']:
                    return float(data['result']['list'][0]['lastPrice'])
        except:
            return None
    return None

def get_coin_kb(coin: str):
    """Создает кнопку Обновить"""
    builder = InlineKeyboardBuilder()
    # Сохраняем имя монеты в callback_data, чтобы бот знал что обновлять
    builder.row(types.InlineKeyboardButton(text="🔄 Обновить", callback_data=f"upd_{coin}"))
    return builder.as_markup()

async def format_coin_message(coin: str):
    """Форматирует текст сообщения с курсами"""
    coin = coin.upper()
    price_rub = await fetch_price(coin, "RUB")
    price_usd = await fetch_price(coin, "USDT")

    if not price_usd:
        return f"❌ Монета <b>{coin}</b> не найдена.", False

    text = f"📊 <b>Курс {coin}</b>\n\n"
    if price_rub:
        text += f"💵 Цена в рублях: <code>{round(price_rub, 2)}₽</code>\n"
    text += f"💵 Цена в долларах: <code>{round(price_usd, 4)}$</code>\n"
    text += f"\n🕒 <i>Обновлено: {asyncio.get_event_loop().time()}</i>" # Для видимости обновления
    
    return text, True

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "💎 <b>Крипто-Терминал 2026</b>\n\n"
        "Используй команду: <code>/c монета</code>\n"
        "Пример: <code>/c BTC</code> или <code>/c TON</code>",
        parse_mode="HTML"
    )

@dp.message(Command("c"))
async def cmd_currency(message: types.Message, command: CommandObject):
    if not command.args:
        await message.answer("Введите символ монеты. Пример: <code>/c BTC</code>")
        return

    coin = command.args.strip().upper()
    text, success = await format_coin_message(coin)
    
    if success:
        await message.answer(text, reply_markup=get_coin_kb(coin), parse_mode="HTML")
    else:
        await message.answer(text, parse_mode="HTML")

@dp.callback_query(F.data.startswith("upd_"))
async def callback_update(callback: types.CallbackQuery):
    # Достаем имя монеты из кнопки
    coin = callback.data.split("_")[1]
    text, success = await format_coin_message(coin)
    
    try:
        # Изменяем старое сообщение на новое
        await callback.message.edit_text(text, reply_markup=get_coin_kb(coin), parse_mode="HTML")
        await callback.answer("Данные обновлены!")
    except Exception:
        # Если цена не изменилась, телеграм выдаст ошибку, просто проигнорируем её
        await callback.answer("Курс пока не изменился")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
