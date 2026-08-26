import os
import threading
from flask import Flask
import requests
from bs4 import BeautifulSoup
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot BCV Activo"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TOKEN:
    print("ERROR: Falta TELEGRAM_TOKEN")
    exit(1)

bot = telebot.TeleBot(TOKEN)

def limpiar_tasa_a_float(texto_tasa):
    try:
        t = texto_tasa.strip()
        if ',' in t:
            t = t.replace('.', '').replace(',', '.')
        return float(t)
    except:
        return 0.0

def obtener_tasas_bcv():
    url = "https://www.bcv.org.ve/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers, verify=False, timeout=10)
        soup = BeautifulSoup(r.content, 'html.parser')
        
        div_dolar = soup.find('div', id='dolar')
        tasa_dolar_str = div_dolar.find('strong').text.strip() if div_dolar and div_dolar.find('strong') else "0"
        
        div_euro = soup.find('div', id='euro')
        tasa_euro_str = div_euro.find('strong').text.strip() if div_euro and div_euro.find('strong') else "0"
        
        return tasa_dolar_str, tasa_euro_str, limpiar_tasa_a_float(tasa_dolar_str), limpiar_tasa_a_float(tasa_euro_str)
    except Exception as e:
        print(f"Error BCV: {e}")
        return "No disponible", "No disponible", 0.0, 0.0

def teclado_fijo():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, is_persistent=True, one_time_keyboard=False)
    markup.add(KeyboardButton("🔄 Actualizar Tasa BCV"))
    return markup

def formatear_bs(valor):
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    texto = (
        "¡Bienvenido al Bot de Tasas del BCV! 🇻🇪\n\n"
        "• Usa el botón de abajo para ver la tasa.\n"
        "• Escribe cualquier monto (ej: 50) y te calculo en Bs."
    )
    bot.send_message(message.chat.id, texto, reply_markup=teclado_fijo(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🔄 Actualizar Tasa BCV")
def mostrar_tasa(message):
    dolar_txt, euro_txt, _, _ = obtener_tasas_bcv()
    if dolar_txt != "No disponible":
        resp = f"📈 **Tasas Oficiales BCV:**\n\n💵 Dólar: `{dolar_txt}` Bs.\n💶 Euro: `{euro_txt}` Bs."
    else:
        resp = "⚠️ BCV caído, intenta en 1 min."
    bot.send_message(message.chat.id, resp, parse_mode="Markdown", reply_markup=teclado_fijo())

@bot.message_handler(func=lambda message: True)
def calcular(message):
    if message.text == "🔄 Actualizar Tasa BCV":
        return

    try:
        monto = float(message.text.strip().replace(',', '.'))
    except ValueError:
        bot.send_message(message.chat.id, "⚠️ Escribe solo un número válido, ej: `50` o `100.50`", parse_mode="Markdown", reply_markup=teclado_fijo())
        return

    dolar_txt, euro_txt, dolar_val, euro_val = obtener_tasas_bcv()
    
    if dolar_val == 0.0:
        bot.send_message(message.chat.id, "⚠️ No pude obtener la tasa del BCV ahora.", reply_markup=teclado_fijo())
        return

    total_dolar = monto * dolar_val
    total_euro = monto * euro_val

    resp = (
        f"🧮 **Cálculo para {monto}:**\n\n"
        f"💵 Dólar (`{dolar_txt}`):\n👉 **{formatear_bs(total_dolar)} Bs.**\n\n"
        f"💶 Euro (`{euro_txt}`):\n👉 **{formatear_bs(total_euro)} Bs.**"
    )
    bot.send_message(message.chat.id, resp, parse_mode="Markdown", reply_markup=teclado_fijo())

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    print("Bot iniciado...")
    bot.infinity_polling(skip_pending=True)
