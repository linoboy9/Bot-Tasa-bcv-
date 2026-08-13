import threading
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot BCV Activo"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_web, daemon=True).start()

import os
import requests
from bs4 import BeautifulSoup
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import urllib3

# Desactivar advertencias SSL para la web del BCV
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Obtiene el Token desde las variables del servidor
TOKEN = os.environ.get("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)

def obtener_datos_bcv():
    url = "https://www.bcv.org.ve/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, verify=False, timeout=12)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 1. Tasa Dólar
        div_dolar = soup.find('div', id='dolar')
        dolar = div_dolar.find('strong').text.strip().replace(',', '.') if div_dolar else "N/D"
        
        # 2. Tasa Euro
        div_euro = soup.find('div', id='euro')
        euro = div_euro.find('strong').text.strip().replace(',', '.') if div_euro else "N/D"
        
        # 3. Fecha Valor
        div_fecha = soup.find('span', class_='date-display-single')
        fecha = div_fecha.text.strip() if div_fecha else "Fecha no disponible"
        
        return {
            "dolar": dolar,
            "euro": euro,
            "fecha": fecha
        }
    except Exception as e:
        print(f"Error extrayendo datos del BCV: {e}")
        return None

# Comando /start o /tasa
@bot.message_handler(commands=['start', 'tasa'])
def cmd_start(message):
    markup = InlineKeyboardMarkup()
    boton = InlineKeyboardButton("💵 Consultar Tasa BCV", callback_data="ver_bcv")
    markup.add(boton)
    
    bot.send_message(
        message.chat.id,
        "👋 ¡Hola! Presiona el botón para obtener la tasa oficial del Banco Central de Venezuela directamente desde su sitio web.",
        reply_markup=markup
    )

# Acción al presionar el botón
@bot.callback_query_handler(func=lambda call: call.data == "ver_bcv")
def callback_bcv(call):
    bot.answer_callback_query(call.id, "Consultando sitio web del BCV...")
    
    datos = obtener_datos_bcv()
    
    if datos:
        mensaje = (
            f"🏦 *BANCO CENTRAL DE VENEZUELA*\n"
            f"📌 *Tipo de Cambio Oficial*\n\n"
            f"💵 **USD:** {datos['dolar']} Bs.\n"
            f"💶 **EUR:** {datos['euro']} Bs.\n\n"
            f"📅 _Fecha Valor: {datos['fecha']}_"
        )
    else:
        mensaje = "⚠️ No se pudo obtener la información del BCV en este momento. Intenta de nuevo más tarde."
        
    bot.send_message(call.message.chat.id, mensaje, parse_mode="Markdown")

if __name__ == "__main__":
    print("Bot iniciando escuchas...")
    bot.infinity_polling()
