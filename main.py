import os
import threading
import time
from flask import Flask
import requests
from bs4 import BeautifulSoup
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
@app.route('/')
def home(): return "Bot BCV Activo - OK"
def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

TOKEN = os.environ.get("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)

# --- CACHE PARA QUE NO SE BUGUEE ---
cache = {"dolar_txt": "0", "euro_txt": "0", "dolar_val": 0.0, "euro_val": 0.0, "timestamp": 0}
CACHE_TIEMPO = 300 # 5 minutos

def limpiar(t):
    try:
        t = t.strip()
        if ',' in t: t = t.replace('.', '').replace(',', '.')
        return float(t)
    except: return 0.0

def obtener_tasas_bcv(forzar=False):
    global cache
    ahora = time.time()
    # Si el cache aun es valido, usalo y no pidas al BCV
    if not forzar and ahora - cache["timestamp"] < CACHE_TIEMPO and cache["dolar_val"] != 0:
        return cache["dolar_txt"], cache["euro_txt"], cache["dolar_val"], cache["euro_val"]

    try:
        r = requests.get("https://www.bcv.org.ve/", headers={'User-Agent':'Mozilla/5.0'}, verify=False, timeout=8)
        soup = BeautifulSoup(r.content, 'html.parser')
        d_txt = soup.find('div', id='dolar').find('strong').text.strip()
        e_txt = soup.find('div', id='euro').find('strong').text.strip()
        d_val = limpiar(d_txt)
        e_val = limpiar(e_txt)
        
        if d_val != 0:
            cache = {"dolar_txt": d_txt, "euro_txt": e_txt, "dolar_val": d_val, "euro_val": e_val, "timestamp": ahora}
            return d_txt, e_txt, d_val, e_val
    except Exception as e:
        print(f"Error BCV: {e}")
    
    # Si falla, devuelve lo que haya en cache aunque este vencido
    if cache["dolar_val"] != 0:
        return cache["dolar_txt"], cache["euro_txt"], cache["dolar_val"], cache["euro_val"]
    return "No disponible", "No disponible", 0.0, 0.0

def teclado():
    mk = ReplyKeyboardMarkup(resize_keyboard=True, is_persistent=True)
    mk.add(KeyboardButton("🔄 Actualizar Tasa BCV"))
    return mk

def fmt(v): return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, "¡Bot BCV listo! 🇻🇪\nEl botón de abajo siempre queda fijo.\nEscribe un monto (ej: 50)", reply_markup=teclado())

@bot.message_handler(func=lambda m: m.text == "🔄 Actualizar Tasa BCV")
def btn_tasa(m):
    # Mostramos que esta trabajando para que no parezca bugueado
    bot.send_chat_action(m.chat.id, 'typing')
    d_txt, e_txt, _, _ = obtener_tasas_bcv(forzar=True) # Forzamos actualizacion
    if d_txt == "No disponible":
        bot.send_message(m.chat.id, "⚠️ BCV no responde, te muestro la última tasa guardada.", reply_markup=teclado())
        d_txt, e_txt, _, _ = obtener_tasas_bcv(forzar=False)
    
    bot.send_message(m.chat.id, f"📈 **Tasas Oficiales BCV:**\n\n💵 Dólar: `{d_txt}` Bs.\n💶 Euro: `{e_txt}` Bs.", parse_mode="Markdown", reply_markup=teclado())

@bot.message_handler(func=lambda message: True)
def calcular(message):
    if message.text.startswith("/"): return
    try:
        monto = float(message.text.strip().replace(',', '.'))
    except:
        bot.send_message(message.chat.id, "⚠️ Solo escribe un número, ej: 50", reply_markup=teclado())
        return
    
    d_txt, e_txt, d_val, e_val = obtener_tasas_bcv()
    if d_val == 0:
        bot.send_message(message.chat.id, "⚠️ No pude obtener tasa, intenta con el botón.", reply_markup=teclado())
        return

    bot.send_message(message.chat.id, 
        f"🧮 **{monto}**\n\n💵 Dólar ({d_txt}): **{fmt(monto*d_val)} Bs**\n💶 Euro ({e_txt}): **{fmt(monto*e_val)} Bs**",
        parse_mode="Markdown", reply_markup=teclado())

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    print("Bot iniciado...")
    # Borra webhook viejo que es lo que lo bugea en Render
    bot.remove_webhook()
    time.sleep(1)
    bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=20)
