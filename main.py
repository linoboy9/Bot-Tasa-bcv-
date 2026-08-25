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

def obtener_tasas_bcv():
    url = "https://www.bcv.org.ve/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    }
    try:
        response = requests.get(url, headers=headers, verify=False, timeout=7)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        div_dolar = soup.find('div', id='dolar')
        tasa_dolar = div_dolar.find('strong').text.strip() if div_dolar else "No disponible"
        
        div_euro = soup.find('div', id='euro')
        tasa_euro = div_euro.find('strong').text.strip() if div_euro else "No disponible"
        
        return tasa_dolar, tasa_euro
    except Exception as e:
        print(f"Error al obtener datos del BCV: {e}")
        return None, None

def crear_teclado():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, persistent=True)
    boton_tasa = KeyboardButton("🔄 Actualizar Tasa BCV")
    markup.add(boton_tasa)
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    texto = (
        "¡Bienvenido al Bot de Tasas del BCV! 🇻🇪\n\n"
        "• Presiona el botón de abajo para consultar las tasas oficiales.\n"
        "• O escribe cualquier monto (ej: `100`) para calcular automáticamente."
    )
    bot.send_message(message.chat.id, texto, reply_markup=crear_teclado(), parse_mode="Markdown")

# Manejador exclusivo para el botón de actualizar
@bot.message_handler(func=lambda message: message.text == "🔄 Actualizar Tasa BCV")
def actualizar_tasas(message):
    tasa_dolar, tasa_euro = obtener_tasas_bcv()
    
    if tasa_dolar and tasa_euro:
        respuesta = (
            "📈 **Tasas Oficiales BCV:**\n\n"
            f"💵 **Dólar:** `{tasa_dolar}` Bs.\n"
            f"💶 **Euro:** `{tasa_euro}` Bs.\n\n"
            "_💡 Tip: Escribe un monto (ej. 100) para calcular automáticamente._"
        )
    else:
        respuesta = "⚠️ La página del BCV está tardando o está caída. Intenta de nuevo en unos minutos."
    
    bot.send_message(message.chat.id, respuesta, reply_markup=crear_teclado(), parse_mode="Markdown")

# Manejador de la calculadora (para cualquier número que escribas)
@bot.message_handler(func=lambda message: True)
def calcular_monto(message):
    texto_usuario = message.text.strip().replace(',', '.')
    
    try:
        monto = float(texto_usuario)
    except ValueError:
        bot.reply_to(message, "⚠️ Por favor, escribe un número válido para calcular (ej. `100`).", reply_markup=crear_teclado())
        return

    tasa_dolar, tasa_euro = obtener_tasas_bcv()
    
    if not tasa_dolar or not tasa_euro or tasa_dolar == "No disponible":
        bot.reply_to(message, "⚠️ No se pudo obtener la tasa del BCV en este momento.", reply_markup=crear_teclado())
        return

    try:
        # Limpieza correcta que ya te funcionaba bien
        val_dolar = float(tasa_dolar.replace('.', '').replace(',', '.'))
        val_euro = float(tasa_euro.replace('.', '').replace(',', '.'))
    except Exception:
        bot.reply_to(message, "⚠️ Error al procesar los valores de las tasas.", reply_markup=crear_teclado())
        return

    total_dolares = monto * val_dolar
    total_euros = monto * val_euro

    res_dolar_fmt = f"{total_dolares:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    res_euro_fmt = f"{total_euros:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    respuesta_calc = (
        f"🧮 **Cálculo para `{monto:,.2f}`:**\n\n"
        f"💵 A tasa del Dólar (`{tasa_dolar} Bs.`):\n"
        f"👉 **`{res_dolar_fmt}` Bs.**\n\n"
        f"💶 A tasa del Euro (`{tasa_euro} Bs.`):\n"
        f"👉 **`{res_euro_fmt}` Bs.**"
    )

    bot.reply_to(message, respuesta_calc, reply_markup=crear_teclado(), parse_mode="Markdown")

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_web, daemon=True)
    server_thread.start()
    
    print("Iniciando bot de Telegram...")
    bot.infinity_polling()
