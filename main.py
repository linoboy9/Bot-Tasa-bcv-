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
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, verify=False, timeout=10)
        soup = BeautifulSoup(r.content, 'html.parser')
        dolar_str = soup.find('div', id='dolar').find('strong').text.strip()
        euro_str = soup.find('div', id='euro').find('strong').text.strip()
        return dolar_str, euro_str, limpiar_tasa_a_float(dolar_str), limpiar_tasa_a_float(euro_str)
    except Exception as e:
        print(f"Error BCV: {e}")
        return "No disponible", "No disponible", 0.0, 0.0

def crear_teclado_fijo():
    # ESTE ES EL TRUCO: ReplyKeyboard en vez de Inline
    markup = ReplyKeyboardMarkup(resize_keyboard=True, is_persistent=True)
    markup.add(KeyboardButton("🔄 Actualizar Tasa BCV"))
    return markup

def formatear_bs(valor):
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    texto = (
        "¡Bienvenido al Bot de Tasas del BCV! 🇻🇪\n\n"
        "• Presiona el botón de abajo para consultar las tasas.\n"
        "• O escribe cualquier cantidad (ej: `100`) y te calculo."
    )
    bot.send_message(message.chat.id, texto, reply_markup=crear_teclado_fijo(), parse_mode="Markdown")

# Ahora el botón también es un mensaje de texto, lo capturamos aquí
@bot.message_handler(func=lambda m: m.text == "🔄 Actualizar Tasa BCV")
def handler_boton_fijo(message):
    tasa_dolar, tasa_euro, _, _ = obtener_tasas_bcv()
    if tasa_dolar != "No disponible":
        respuesta = f"📈 **Tasas Oficiales BCV:**\n\n💵 **Dólar:** `{tasa_dolar}` Bs.\n💶 **Euro:** `{tasa_euro}` Bs."
    else:
        respuesta = "⚠️ BCV caído, intenta en 1 min."
    bot.send_message(message.chat.id, respuesta, parse_mode="Markdown", reply_markup=crear_teclado_fijo())

@bot.message_handler(func=lambda message: True)
def calcular_monto(message):
    # Si es el botón, ya lo manejamos arriba
    if message.text == "🔄 Actualizar Tasa BCV":
        return
    try:
        monto = float(message.text.strip().replace(',', '.'))
    except ValueError:
        return # Ignoramos si escribe otra cosa que no sea número

    txt_dolar, txt_euro, val_dolar, val_euro = obtener_tasas_bcv()
    if val_dolar == 0.0:
        bot.reply_to(message, "⚠️ No pude obtener tasa del BCV ahora.", reply_markup=crear_teclado_fijo())
        return

    respuesta = (
        f"🧮 **Cálculo para `{monto}`:**\n\n"
        f"💵 Dólar (`{txt_dolar}`):\n👉 **{formatear_bs(monto * val_dolar)} Bs.**\n\n"
        f"💶 Euro (`{txt_euro}`):\n👉 **{formatear_bs(monto * val_euro)} Bs.**"
    )
    bot.reply_to(message, respuesta, parse_mode="Markdown", reply_markup=crear_teclado_fijo())

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    bot.infinity_polling(skip_pending=True)
