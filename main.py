Import os
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

def limpiar_tasa_a_float(texto_tasa):
    """Limpia el texto del BCV (ej: '785,0693' o '36.123,45') a un float real."""
    try:
        # Quitamos espacios y reemplazamos la coma por punto para el decimal
        limpio = texto_tasa.strip().replace('.', '').replace(',', '.')
        return float(limpio)
    except Exception:
        return 0.0

def obtener_tasas_bcv():
    url = "https://www.bcv.org.ve/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    }
    try:
        response = requests.get(url, headers=headers, verify=False, timeout=7)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        div_dolar = soup.find('div', id='dolar')
        tasa_dolar_str = div_dolar.find('strong').text.strip() if div_dolar else "0"
        
        div_euro = soup.find('div', id='euro')
        tasa_euro_str = div_euro.find('strong').text.strip() if div_euro else "0"
        
        # Obtenemos los valores flotantes corregidos
        val_dolar = limpiar_tasa_a_float(tasa_dolar_str)
        val_euro = limpiar_tasa_a_float(tasa_euro_str)
        
        return tasa_dolar_str, tasa_euro_str, val_dolar, val_euro
               
    except Exception as e:
        print(f"Error al obtener datos del BCV: {e}")
        return "No disponible", "No disponible", 0.0, 0.0

def crear_markup():
    markup = InlineKeyboardMarkup()
    boton_tasa = InlineKeyboardButton("🔄 Actualizar Tasa BCV", callback_data="ver_tasa")
    markup.add(boton_tasa)
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    texto = (
        "¡Bienvenido al Bot de Tasas del BCV! 🇻🇪\n\n"
        "• Presiona el botón para consultar las tasas oficiales.\n"
        "• O **escribe cualquier cantidad** (ej: `100` o `50.50`) para calcular su equivalencia en Bolívares."
    )
    bot.send_message(message.chat.id, texto, reply_markup=crear_markup(), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "ver_tasa")
def callback_ver_tasa(call):
    bot.answer_callback_query(call.id, "Consultando al BCV...")
    
    tasa_dolar, tasa_euro, _, _ = obtener_tasas_bcv()
    
    if tasa_dolar != "No disponible" and tasa_euro != "No disponible":
        respuesta = (
            "📈 **Tasas Oficiales BCV:**\n\n"
            f"💵 **Dólar:** `{tasa_dolar}` Bs.\n"
            f"💶 **Euro:** `{tasa_euro}` Bs.\n\n"
            "_💡 Tip: Escribe un monto (ej. 100) para calcular automáticamente._"
        )
    else:
        respuesta = "⚠️ La página del BCV está tardando o está caída. Intenta de nuevo en unos minutos."
    
    try:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=respuesta,
            parse_mode="Markdown",
            reply_markup=crear_markup()
        )
    except Exception:
        bot.send_message(call.message.chat.id, respuesta, parse_mode="Markdown", reply_markup=crear_markup())

@bot.message_handler(func=lambda message: True)
def calcular_monto(message):
    texto_usuario = message.text.strip().replace(',', '.')
    
    try:
        monto = float(texto_usuario)
    except ValueError:
        bot.reply_to(message, "⚠️ Por favor, escribe solo un número válido para calcular (ej. `100` o `50.50`).", parse_mode="Markdown")
        return

    tasa_dolar_txt, tasa_euro_txt, val_dolar, val_euro = obtener_tasas_bcv()
    
    if val_dolar == 0.0 or val_euro == 0.0:
        bot.reply_to(message, "⚠️ No se pudo obtener la tasa del BCV en este momento para hacer el cálculo. Intenta más tarde.")
        return

    total_dolares = monto * val_dolar
    total_euros = monto * val_euro

    # Formateamos el resultado con separador de miles por puntos y decimales por comas
    res_dolar_fmt = f"{total_dolares:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    res_euro_fmt = f"{total_euros:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    respuesta_calc = (
        f"🧮 **Cálculo para `{monto:,.2f}`:**\n\n"
        f"💵 A tasa del Dólar (`{tasa_dolar_txt} Bs.`):\n"
        f"👉 **`{res_dolar_fmt}` Bs.**\n\n"
        f"💶 A tasa del Euro (`{tasa_euro_txt} Bs.`):\n"
        f"👉 **`{res_euro_fmt}` Bs.**"
    )

    bot.reply_to(message, respuesta_calc, parse_mode="Markdown")

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_web, daemon=True)
    server_thread.start()
    
    print("Iniciando bot de Telegram...")
    bot.infinity_polling()
