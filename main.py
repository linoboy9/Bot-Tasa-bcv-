import os
import threading
from flask import Flask
import requests
from bs4 import BeautifulSoup
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import urllib3

# Desactivar advertencias SSL para la web del BCV
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configurar el servidor web falso para evitar el Time Out en Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot BCV Activo"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# Obtener el Token del bot desde las variables de entorno de Render
TOKEN = os.environ.get("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)

def obtener_tasas_bcv():
    url = "https://www.bcv.org.ve/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    }
    try:
        # Añadimos timeout=7 para que si el BCV no responde rápido, falle de forma limpia
        response = requests.get(url, headers=headers, verify=False, timeout=7)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extraer tasa del Dólar
        div_dolar = soup.find('div', id='dolar')
        tasa_dolar = div_dolar.find('strong').text.strip() if div_dolar else "No disponible"
        
        # Extraer tasa del Euro
        div_euro = soup.find('div', id='euro')
        tasa_euro = div_euro.find('strong').text.strip() if div_euro else "No disponible"
        
        return tasa_dolar, tasa_euro
    except Exception as e:
        print(f"Error al obtener datos del BCV: {e}")
        return None, None

# Comando /start que envía un mensaje de bienvenida con el botón interactivo
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = InlineKeyboardMarkup()
    boton_tasa = InlineKeyboardButton("📊 Ver Tasa del BCV", callback_data="ver_tasa")
    markup.add(boton_tasa)
    
    texto_bienvenida = (
        "¡Bienvenido al Bot de Tasas del BCV! 🇻🇪\n\n"
        "Presiona el botón de abajo para consultar las tasas oficiales actualizadas del dólar y del euro:"
    )
    bot.send_message(message.chat.id, texto_bienvenida, reply_markup=markup)

# Manejar la acción cuando presionan el botón
@bot.callback_query_handler(func=lambda call: call.data == "ver_tasa")
def callback_ver_tasa(call):
    bot.answer_callback_query(call.id, "Consultando al BCV...")
    tasa_dolar, tasa_euro = obtener_tasas_bcv()
    
    if tasa_dolar and tasa_euro:
        respuesta = (
            "📈 **Tasas Oficiales BCV:**\n\n"
            f"💵 **Dólar:** {tasa_dolar} Bs.\n"
            f"💶 **Euro:** {tasa_euro} Bs."
        )
    else:
        respuesta = "⚠️ La página del BCV está tardando mucho en responder o se encuentra caída en este momento. Inténtalo de nuevo en unos minutos."
    
    bot.send_message(call.message.chat.id, respuesta, parse_mode="Markdown")

if __name__ == "__main__":
    # 1. Iniciar Flask en un hilo en segundo plano para cumplir con el puerto de Render
    server_thread = threading.Thread(target=run_web, daemon=True)
    server_thread.start()
    
    # 2. Iniciar el bot de Telegram en el proceso principal
    print("Iniciando bot de Telegram...")
    bot.infinity_polling()
