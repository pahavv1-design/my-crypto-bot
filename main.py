import telebot
from telebot import types
import requests
import sqlite3
import time

# ================= НАСТРОЙКИ =================
BOT_TOKEN = '8764944988:AAGgtR8fueiBlAIlnLjjCgze_wivbO4Pm20'
ADMIN_ID = 8432377192  # ВАШ ТЕЛЕГРАМ ID (только цифры)
# =============================================

bot = telebot.TeleBot(BOT_TOKEN)

# Подключение к базе данных
conn = sqlite3.connect('users.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
conn.commit()

# --- СИСТЕМА ПАМЯТИ (КЭШ) ---
CACHE_TIME = 60 
last_rates = None
last_fetch_time = 0

# НОВАЯ СУПЕР-ФУНКЦИЯ (KuCoin + Банковский курс)
def get_crypto_rates():
    global last_rates, last_fetch_time

    if time.time() - last_fetch_time < CACHE_TIME and last_rates:
        return last_rates

    try:
        # 1. Берем курс крипты с KuCoin (Эта биржа НЕ блокирует американские сервера)
        ton_req = requests.get("https://api.kucoin.com/api/v1/market/orderbook/level1?symbol=TON-USDT").json()
        ton_usd = float(ton_req['data']['price'])

        btc_req = requests.get("https://api.kucoin.com/api/v1/market/orderbook/level1?symbol=BTC-USDT").json()
        btc_usd = float(btc_req['data']['price'])
        
        # 2. Берем курс доллара к рублю с международного API
        rub_api = requests.get("https://api.exchangerate-api.com/v4/latest/USD").json()
        usd_rub = float(rub_api['rates']['RUB'])

        # Наценка P2P рынка для USDT
        usdt_rub = usd_rub + 2.50

        # 3. Умножаем доллары на курс рубля
        ton_rub = ton_usd * usdt_rub
        btc_rub = btc_usd * usdt_rub
        
        # Сохраняем результат
        last_rates = {
            'ton_rub': round(ton_rub, 2),
            'ton_usd': round(ton_usd, 3),
            'usdt_rub': round(usdt_rub, 2),
            'usdt_usd': 1.00,
            'btc_rub': round(btc_rub, 0),
            'btc_usd': round(btc_usd, 0)
        }
        
        last_fetch_time = time.time() 
        return last_rates
    except Exception as e:
        print(f"Ошибка получения курса: {e}")
        return None

# Команда /start
@bot.message_handler(commands=['start'])
def start_message(message):
    user_id = message.chat.id
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("💰 Узнать курс")
    btn2 = types.KeyboardButton("🧮 Калькулятор TON")
    btn3 = types.KeyboardButton("👤 Мой профиль")
    markup.add(btn1, btn2, btn3)

    bot.send_message(user_id, "Привет! 👋\nЯ твой финансовый помощник.\n\nВыбери нужное действие в меню ниже 👇", reply_markup=markup)

# Обработка кнопки "Узнать курс"
@bot.message_handler(func=lambda message: message.text == "💰 Узнать курс")
def show_rates(message):
    rates = get_crypto_rates()
    
    if rates:
        text = (f"📊 <b>Актуальный рыночный курс:</b>\n\n"
                f"🟠 <b>BTC:</b> {rates['btc_rub']:,.0f} ₽   |   {rates['btc_usd']:,.0f} $\n"
                f"💎 <b>TON:</b> {rates['ton_rub']} ₽   |   {rates['ton_usd']} $\n"
                f"💵 <b>USDT:</b> {rates['usdt_rub']} ₽   |   1.00 $\n\n"
                f"<i>Обновлено только что 🔄</i>")
        bot.send_message(message.chat.id, text, parse_mode="HTML")
    else:
        bot.send_message(message.chat.id, "❌ Не удалось получить курс. Сервера загружены, попробуйте еще раз.")

# Обработка кнопки "Профиль"
@bot.message_handler(func=lambda message: message.text == "👤 Мой профиль")
def show_profile(message):
    user_id = message.chat.id
    first_name = message.from_user.first_name
    
    text = (f"👤 <b>Ваш профиль:</b>\n\n"
            f"Имя: <b>{first_name}</b>\n"
            f"Ваш Telegram ID: <code>{user_id}</code>\n\n"
            f"🟢 Статус: Пользователь бота")
    bot.send_message(user_id, text, parse_mode="HTML")

# Обработка кнопки "Калькулятор"
@bot.message_handler(func=lambda message: message.text == "🧮 Калькулятор TON")
def calc_start(message):
    msg = bot.send_message(message.chat.id, "✍️ <b>Введите количество TON</b> (просто цифру), чтобы узнать их стоимость:", parse_mode="HTML")
    bot.register_next_step_handler(msg, process_calc)

def process_calc(message):
    if message.text in ["💰 Узнать курс", "👤 Мой профиль"]:
        bot.send_message(message.chat.id, "Калькулятор отменен.")
        return

    try:
        amount = float(message.text.replace(',', '.'))
        rates = get_crypto_rates()
        
        if rates:
            rub_sum = amount * rates['ton_rub']
            usd_sum = amount * rates['ton_usd']
            
            text = (f"🧮 <b>Калькулятор:</b>\n\n"
                    f"💎 <b>{amount} TON</b> это:\n"
                    f"🇷🇺 {rub_sum:,.2f} Рублей\n"
                    f"🇺🇸 {usd_sum:,.2f} Долларов")
            bot.send_message(message.chat.id, text, parse_mode="HTML")
        else:
            bot.send_message(message.chat.id, "❌ Ошибка получения курса для расчета.")
            
    except ValueError:
        bot.send_message(message.chat.id, "❌ Ошибка! Нужно ввести просто число (например: 10 или 5.5). Нажмите кнопку калькулятора еще раз.")

# ================= АДМИН ПАНЕЛЬ =================
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "У вас нет прав администратора.")
        return

    markup = types.InlineKeyboardMarkup()
    btn_broadcast = types.InlineKeyboardButton(text="📢 Сделать рассылку", callback_data="broadcast")
    markup.add(btn_broadcast)
    
    cursor.execute("SELECT COUNT(*) FROM users")
    users_count = cursor.fetchone()[0]

    bot.send_message(message.chat.id, f"🛠 <b>Админ-панель</b>\n\nВсего пользователей: {users_count}", reply_markup=markup, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data == "broadcast")
def broadcast_step_1(call):
    if call.message.chat.id != ADMIN_ID:
        return
    msg = bot.send_message(call.message.chat.id, "📝 Отправьте сообщение для рассылки всем пользователям:")
    bot.register_next_step_handler(msg, broadcast_step_2)

def broadcast_step_2(message):
    text_to_send = message.text
    if not text_to_send:
        bot.send_message(message.chat.id, "❌ Отменено. Можно отправлять только текст.")
        return

    bot.send_message(message.chat.id, "⏳ Рассылка началась...")
    
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    
    success_count = 0
    for user in users:
        try:
            bot.send_message(user[0], text_to_send)
            success_count += 1
            time.sleep(0.05)
        except Exception:
            pass

    bot.send_message(message.chat.id, f"✅ Рассылка завершена!\nУспешно отправлено: {success_count} пользователям.")

if __name__ == '__main__':
    print("Бот успешно запущен!")
    bot.infinity_polling()
