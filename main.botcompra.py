import os
import sqlite3
import datetime
import random
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

# Cargar variables de entorno
BOT_TOKEN = os.getenv("BOT_TOKEN")
# ID del chat o canal de Avisos (ej: -100123456789 o id personal)
AVISOS_CHAT_ID = os.getenv("CHAT_ID") 

ADMINS = ["@kirschteiinz", "@zilbato"]

# --- BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect("subscripciones.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subs (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            fecha_fin TEXT
        )
    """)
    conn.commit()
    conn.close()

def get_db_connection():
    return sqlite3.connect("subscripciones.db")

# --- FUNCIONES AUXILIARES ---
async def verificar_cambio_username(context: ContextTypes.DEFAULT_TYPE, user_id: int, current_username: str):
    """Verifica si el usuario cambió su @username y avisa al canal."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM subs WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    if row and row[0] and row[0].lower() != current_username.lower():
        old_username = row[0]
        cursor.execute("UPDATE subs SET username = ? WHERE user_id = ?", (current_username, user_id))
        conn.commit()
        
        # Avisar del cambio
        mensaje = f"⚠️ **Aviso de cambio de usuario:**\nEl usuario con ID `{user_id}` cambió de {old_username} a {current_username}."
        await context.bot.send_message(chat_id=AVISOS_CHAT_ID, text=mensaje, parse_mode="Markdown")
    
    conn.close()

# --- COMANDOS ---

# /add 25 días @user [ID_OPCIONAL]
async def add_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        # Estructura: /add <dias> días <@username> [user_id]
        dias = int(args[0])
        username = args[2] if len(args) > 2 else args[1]
        
        # ID normal de 6 dígitos si no se especifica uno manualmente
        user_id = int(args[3]) if len(args) > 3 else random.randint(100000, 999999) 

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Comprobar si ya existe por username para actualizar su registro
        cursor.execute("SELECT user_id, fecha_fin FROM subs WHERE username = ?", (username,))
        row = cursor.fetchone()
        
        hoy = datetime.datetime.now()
        
        if row:
            existing_id, fecha_str = row
            fecha_actual_fin = datetime.datetime.fromisoformat(fecha_str)
            base_fecha = max(hoy, fecha_actual_fin)
            nueva_fecha = base_fecha + datetime.timedelta(days=dias)
            cursor.execute("UPDATE subs SET fecha_fin = ? WHERE user_id = ?", 
                           (nueva_fecha.isoformat(), existing_id))
        else:
            nueva_fecha = hoy + datetime.timedelta(days=dias)
            cursor.execute("INSERT INTO subs (user_id, username, fecha_fin) VALUES (?, ?, ?)", 
                           (user_id, username, nueva_fecha.isoformat()))
            
        conn.commit()
        conn.close()

        await update.message.reply_text(f"⸜(*ˊᗜˋ*)⸝  ¡𝓢e añadieron {dias} días a la sub de {username}!")

    except Exception as e:
        await update.message.reply_text("❌ Uso correcto: `/add 25 días @user` o `/add 25 días @user ID_USUARIO`", parse_mode="Markdown")

# /rest 10 días @user
async def rest_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        dias = int(args[0])
        username = args[2] if len(args) > 2 else args[1]

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, fecha_fin FROM subs WHERE username = ?", (username,))
        row = cursor.fetchone()

        if row:
            user_id, fecha_str = row
            fecha_actual = datetime.datetime.fromisoformat(fecha_str)
            nueva_fecha = fecha_actual - datetime.timedelta(days=dias)
            
            cursor.execute("UPDATE subs SET fecha_fin = ? WHERE user_id = ?", (nueva_fecha.isoformat(), user_id))
            conn.commit()
            conn.close()

            await update.message.reply_text(f"(๑´`๑)  𝓢e restaron {dias} días a la sub de {username}.")
        else:
            conn.close()
            await update.message.reply_text(f"❌ No se encontró a {username} en la base de datos.")

    except Exception as e:
        await update.message.reply_text("❌ Uso correcto: `/rest 10 días @user`", parse_mode="Markdown")

# /sub @user -> Consulta el estado de un usuario específico
async def check_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await update.message.reply_text("❌ Uso correcto: `/sub @user`", parse_mode="Markdown")
            return

        username = context.args[0]

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, fecha_fin FROM subs WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()

        if row:
            user_id, fecha_str = row
            hoy = datetime.datetime.now()
            fecha_fin = datetime.datetime.fromisoformat(fecha_str)
            dias_restantes = (fecha_fin - hoy).days + 1

            if dias_restantes > 0:
                await update.message.reply_text(
                    f"✨ **Estado de suscripción:**\n"
                    f"👤 Usuario: {username}\n"
                    f"🆔 ID: `{user_id}`\n"
                    f"⏳ Estado: Quedan **{dias_restantes} días** de suscripción.",
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text(
                    f"⚠️ **Estado de suscripción:**\n"
                    f"👤 Usuario: {username}\n"
                    f"🆔 ID: `{user_id}`\n"
                    f"❌ La suscripción ya se encuentra **caducada**.",
                    parse_mode="Markdown"
                )
        else:
            await update.message.reply_text(f"❌ No se encontró información de suscripción para {username}.")

    except Exception as e:
        await update.message.reply_text("❌ Uso correcto: `/sub @user`", parse_mode="Markdown")

# /subs
async def list_subs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, fecha_fin FROM subs")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("📜 No hay suscripciones activas registradas.")
        return

    hoy = datetime.datetime.now()
    mensaje = "📋 **Lista de Suscripciones Activas:**\n\n"

    for user_id, username, fecha_str in rows:
        fecha_fin = datetime.datetime.fromisoformat(fecha_str)
        dias_restantes = (fecha_fin - hoy).days + 1

        if dias_restantes > 0:
            mensaje += f"• {username} (ID: `{user_id}`): le quedan **{dias_restantes} días**\n"
        else:
            mensaje += f"• {username} (ID: `{user_id}`): ❌ **Caducada**\n"

    await update.message.reply_text(mensaje, parse_mode="Markdown")

# Tarea automática que revisa cada día si caducan subs
async def comprobar_caducidades_diarias(context: ContextTypes.DEFAULT_TYPE):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, fecha_fin FROM subs")
    rows = cursor.fetchall()
    conn.close()

    hoy = datetime.datetime.now().date()
    admins_str = " ".join(ADMINS)

    for user_id, username, fecha_str in rows:
        fecha_fin = datetime.datetime.fromisoformat(fecha_str).date()
        
        # Si finaliza justo hoy
        if fecha_fin == hoy:
            dias_totales = (datetime.datetime.fromisoformat(fecha_str) - datetime.datetime.now()).days + 1
            if dias_totales <= 0:
                dias_totales = 1

            mensaje = (
                f"₍˶ᵔ ˕ ᵔ˶₎  𝓗ey admins! {admins_str}\n"
                f"la sub de {username} de {dias_totales} días finaliza hoy ¡no olviden preguntar por su renovación!"
            )
            await context.bot.send_message(chat_id=AVISOS_CHAT_ID, text=mensaje)

# MAIN
def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("add", add_sub))
    app.add_handler(CommandHandler("rest", rest_sub))
    app.add_handler(CommandHandler("sub", check_sub))
    app.add_handler(CommandHandler("subs", list_subs))

    # Tarea programada para revisar vencimientos cada 24h
    job_queue = app.job_queue
    if job_queue:
        job_queue.run_repeating(comprobar_caducidades_diarias, interval=86400, first=10)

    print("Bot en marcha...")
    app.run_polling()

if __name__ == "__main__":
    main()
