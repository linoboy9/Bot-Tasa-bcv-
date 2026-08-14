import os
import threading
from flask import Flask
import requests
from bs4 import BeautifulSoup
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
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

def crear_markup():
    markup = InlineKeyboardMarkup()
    boton_tasa = InlineKeyboardButton("🔄 Actualizar Tasa BCV", callback_data="ver_tasa")
    markup.add(boton_tasa)
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    texto = (
        "¡Bienvenido al Bot de Tasas del BCV! 🇻🇪\n\n"
        "Presiona el botón de abajo para consultar las tasas oficiales:"
    )
    bot.send_message(message.chat.id, texto, reply_markup=crear_markup())

@bot.callback_query_handler(func=lambda call: call.data == "ver_tasa")
def callback_ver_tasa(call):
    bot.answer_callback_query(call.id, "Consultando al BCV...")
    
    tasa_dolar, tasa_euro = obtener_tasas_bcv()
    
    if tasa_dolar and tasa_euro:
        respuesta = (
            "📈 **Tasas Oficiales BCV:**\n\n"
            f"💵 **Dólar:** `{tasa_dolar}` Bs.\n"
            f"💶 **Euro:** `{tasa_euro}` Bs.\n\n"
            "_Última actualización_"
        )
    else:
        respuesta = "⚠️ La página del BCV está tardando o está caída. Intenta de nuevo en unos minutos."
    
    # ← ESTE ES EL CAMBIO IMPORTANTE
    try:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=respuesta,
            parse_mode="Markdown",
            reply_markup=crear_markup()
        )
    except Exception as e:
        # Por si el mensaje es muy viejo o hay algún error, manda uno nuevo
        bot.send_message(call.message.chat.id, respuesta, parse_mode="Markdown", reply_markup=crear_markup())

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_web, daemon=True)
    server_thread.start()
    
    print("Iniciando bot de Telegram...")
    bot.infinity_polling()
