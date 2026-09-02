import telebot
from telebot import types
import random
import threading
import time
import re
import os
from datetime import datetime, timedelta

TOKEN = os.environ["TOKEN"]
bot = telebot.TeleBot(TOKEN)

# --- CONFIGURACIÓN Y PERSISTENCIA DE PERMISOS GLOBAL ---
ADMINS_FILE = "admins.txt"
ADMINS_PERMITIDOS = set()
SUPER_ADMIN = "kirschteiinz"  # Usuario de telegram autorizado sin @

def cargar_admins():
    """Carga los IDs de administradores guardados de forma permanente."""
    if os.path.exists(ADMINS_FILE):
        with open(ADMINS_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line.isdigit():
                    ADMINS_PERMITIDOS.add(int(line))

def guardar_admins():
    """Guarda de forma permanente la lista actual de administradores."""
    with open(ADMINS_FILE, "w") as f:
        for admin_id in ADMINS_PERMITIDOS:
            f.write(f"{admin_id}\n")

# Cargar admins al iniciar la aplicación
cargar_admins()

def es_admin(chat_id, user_id):
    return user_id in ADMINS_PERMITIDOS

# --- BASE DE DATOS SIMPLE DE SUSCRIPCIONES ---
# Formato: {username: {"dias": int, "user_id": int, "chat_id": int, "fecha_fin": datetime}}
suscripciones = {}

# --- PACK DE STICKERS DE CHERRIEBOT ---
STICKERS_CHERRIE = [
    "CAACAgEAAxkBAANHaoVbwH1bR16BovjZpvbzdmYAAcv5AAJKCAACh1YpROPnWzoUB7hkPQQ",
    "CAACAgEAAxkBAANJaoVbxFwCt6v7Dc4Bq5MBVviJkq0AAkIGAAKaKilEw6n5UhHxucY9BA",
    "CAACAgEAAxkBAANLaoVbxu0C4Pf13Q4h4--008tHtA0AAjwHAALY5ShExZIILPgB8XU9BA",
    "CAACAgEAAxkBAANNaoVbx0HIrfh3HaoEnRnq2TiF2FYAAgoHAAJDLjFED9e__RIuw0g9BA",
    "CAACAgEAAxkBAANPaoVbyYS2PuWDTuGSdGdWwcA7onQAAp8IAALviDFErpsOg5jJa4g9BA",
    "CAACAgEAAxkBAANRaoVby-CNkO8cMAw7x6E2yUThMaoAAtkGAALl9SlEbGxRRm1A0vM9BA"
]

STICKER_RED = "CAACAgEAAxkBAAMEaoniIkZBty-fZAaO2qRWlnmSLz8AArEKAAKZBFFE4Fo8s2EZTbU9BA"
STICKER_PINK = "CAACAgEAAxkBAAMCaoniHkzsWaDk9R6Omme6uuj8vUAAAgkLAAK8SFBEsHO2EgaHmJs9BA"

# --- ESTADOS GLOBALES Y REGISTROS ---
sorteos = {}
puntos_sistema = {}          # {username: puntos_int}
quiz_aciertos = {}           # {username: total_aciertos_int}
mineria_historico = {}       # {username: puntos_acumulados_int}
victorias_historico = {}     # {username: total_victorias_int}
usuarios_ids = {}            # {username: user_id} para poder enviar PM

def registrar_victoria(username):
    victorias_historico[username] = victorias_historico.get(username, 0) + 1

def get_thread_id(message):
    return message.message_thread_id if message.is_topic_message else None


# --- GESTIÓN DE SUSCRIPCIONES FORMATO CORTO ---

@bot.message_handler(commands=['addsub'])
def agregar_suscripcion(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin autorizado.", message_thread_id=thread_id)
        return

    args = message.text.split()
    if len(args) < 3:
        bot.send_message(chat_id, "✦ Uso: /addsub @usuario [días]", message_thread_id=thread_id)
        return

    usuario = args[1].replace('@', '').lower()
    try:
        dias = int(args[2])
    except ValueError:
        bot.send_message(chat_id, " (╥﹏╥) Los días deben ser un número entero.", message_thread_id=thread_id)
        return

    target_id = usuarios_ids.get(usuario, message.from_user.id)
    fecha_fin = datetime.now() + timedelta(days=dias)

    suscripciones[usuario] = {
        "dias": dias,
        "user_id": target_id,
        "chat_id": chat_id,
        "fecha_fin": fecha_fin
    }

    bot.send_message(chat_id, f"✦ ¡Suscripción agregada/actualizada para @{usuario} por {dias} días! ♡", message_thread_id=thread_id)


@bot.message_handler(commands=['subs'])
def listar_suscripciones(message):
    chat_id, user_id = message.chat.id, message.from_user.id
    thread_id = get_thread_id(message)

    if not es_admin(chat_id, user_id):
        bot.send_message(chat_id, " (╥﹏╥)  no eres admin autorizado.", message_thread_id=thread_id)
        return

    if not suscripciones:
        bot.send_message(chat_id, " (╥﹏╥) No hay suscripciones activas registradas.", message_thread_id=thread_id)
        return

    bloques = []
    ahora = datetime.now()

    for user, data in suscripciones.items():
        restantes = (data["fecha_fin"] - ahora).days
        if restantes < 0:
            restantes = 0

        bloque = (
            f"[〄] 𝗬𝗼𝘀𝗵𝗶 𝗖𝗵𝗸 | 𝗜𝗗\n"
            f"[〄] Usuario: @{user}\n"
            f"[〄] ID Usuario: {data['user_id']}\n"
            f"[〄] ID Chat: {data['chat_id']}\n"
            f"[〄] Días restantes: {restantes} día(s)"
        )
        bloques.append(bloque)

    texto_final = "\n\n".join(bloques)
    bot.send_message(chat_id, texto_final, message_thread_id=thread_id)


@bot.message_handler(commands=['sub'])
def consultar_sub_individual(message):
    chat_id = message.chat.id
    thread_id = get_thread_id(message)
    args = message.text.split()

    # Si se especificó usuario (ej: /sub @zilbato)
    if len(args) >= 2:
        usuario = args[1].replace('@', '').lower()
    else:
        # Si no pone usuario, consulta el propio
        usuario = (message.from_user.username if message.from_user.username else message.from_user.first_name).lower()

    if usuario not in suscripciones:
        bot.send_message(chat_id, f" (╥﹏╥)  El usuario @{usuario} no tiene una suscripción activa.", message_thread_id=thread_id)
        return

    data = suscripciones[usuario]
    ahora = datetime.now()
    dias_restantes = (data["fecha_fin"] - ahora).days

    if dias_restantes < 0:
        dias_restantes = 0

    texto = (
        f"[〄] 𝗬𝗼𝘀𝗵𝗶 𝗖𝗵𝗸 | 𝗜𝗗\n"
        f"[〄] Usuario: @{usuario}\n"
        f"[〄] ID Usuario: {data['user_id']}\n"
        f"[〄] ID Chat: {data['chat_id']}\n"
        f"[〄] Días restantes: {dias_restantes} día(s)"
    )

    bot.send_message(chat_id, texto, message_thread_id=thread_id)


# --- REGISTRO DE USUARIOS AUTOMÁTICO EN INTERACCIONES ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    username = (message.from_user.username if message.from_user.username else message.from_user.first_name).lower()
    usuarios_ids[username] = message.from_user.id
    if message.chat.type == 'private':
        nombre_usuario = message.from_user.first_name
        bot.send_message(
            message.chat.id, 
            f"૮ ˶• ˔ •˶ ა   ¡holi, {nombre_usuario}! soy cherrie, el bot oficial de cherrys que ayuda en dinámicas para que tú te diviertas y consigas los mejores premios ♡."
        )

# --- INICIO DEL BOT ---
if __name__ == "__main__":
    bot.infinity_polling()
