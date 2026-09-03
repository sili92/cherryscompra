import os
import sqlite3
import datetime
import random
import html
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
        
        # Avisar del cambio usando HTML para evitar problemas con _
        mensaje = (
            f"⚠️ <b>Aviso de cambio de usuario:</b>\n"
            f"El usuario con ID <code>{user_id}</code> cambió de {html.escape(old_username)} "
            f"a {html.escape(current_username)}."
        )
        await context.bot.send_message(chat_id=AVISOS_CHAT_ID, text=mensaje, parse_mode="HTML")
    
    conn.close()

# --- COMANDOS ---

# /add 25 días @user_con_guion [ID_OPCIONAL]
async def add_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        if len(args) < 2:
            raise ValueError("Faltan argumentos")

        dias = int(args[0])
        
        # Buscar el username (que empieza por @) entre los argumentos
        username = None
        user_id = None
        
        for arg in args[1:]:
            if arg.startswith("@"):
                username = arg
            elif arg.isdigit():
                user_id = int(arg)
                
        if not username:
            # Fallback en caso de que no hayan puesto @
            username = args[2] if len(args) > 2 and not args[1].isdigit() else args[1]
            if not username.startswith("@"):
                username = f"@{username}"

        if not user_id:
            user_id = random.randint(100000, 999999)

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

        # Se escapa el texto para HTML
        safe_user = html.escape(username)
        await update.message.reply_html(f"⸜(*ˊᗜˋ*)⸝ ¡Se añadieron {dias} días a la sub de <b>{safe_user}</b>!")

    except Exception as e:
        await update.message.reply_html(
            "❌ Uso correcto: <code>/add 25 días @user</code> o <code>/add 25 días @user ID_USUARIO</code>"
        )

# /rest 10 días @user
async def rest_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        dias = int(args[0])
        
        # Obtener el username limpiamente
        username = None
        for arg in args[1:]:
            if arg.startswith("@"):
                username = arg
                break
        if not username:
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

            safe_user = html.escape(username)
            await update.message.reply_html(f"(๑´`๑) Se restaron {dias} días a la sub de <b>{safe_user}</b>.")
        else:
            conn.close()
            safe_user = html.escape(username)
            await update.message.reply_html(f"❌ No se encontró a {safe_user} en la base de datos.")

    except Exception as e:
        await update.message.reply_html("❌ Uso correcto: <code>/rest 10 días @user</code>")

# /sub @user -> Consulta el estado de un usuario específico
async def check_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await update.message.reply_html("❌ Uso correcto: <code>/sub @user</code>")
            return

        username = context.args[0]

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, fecha_fin FROM subs WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()

        safe_user = html.escape(username)

        if row:
            user_id, fecha_str = row
            hoy = datetime.datetime.now()
            fecha_fin = datetime.datetime.fromisoformat(fecha_str)
            dias_restantes = (fecha_fin - hoy).days + 1

            if dias_restantes > 0:
                await update.message.reply_html(
                    f"✨ <b>Estado de suscripción:</b>\n"
                    f"👤 Usuario: {safe_user}\n"
                    f"🆔 ID: <code>{user_id}</code>\n"
                    f"⏳ Estado: Quedan <b>{dias_restantes} días</b> de suscripción."
                )
            else:
                await update.message.reply_html(
                    f"⚠️ <b>Estado de suscripción:</b>\n"
                    f"👤 Usuario: {safe_user}\n"
                    f"🆔 ID: <code>{user_id}</code>\n"
                    f"❌ La suscripción ya se encuentra <b>caducada</b>."
                )
        else:
            await update.message.reply_html(f"❌ No se encontró información de suscripción para {safe_user}.")

    except Exception as e:
        await update.message.reply_html("❌ Uso correcto: <code>/sub @user</code>")

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
    mensaje = "📋 <b>Lista de Suscripciones Activas:</b>\n\n"

    for user_id, username, fecha_str in rows:
        fecha_fin = datetime.datetime.fromisoformat(fecha_str)
        dias_restantes = (fecha_fin - hoy).days + 1
        safe_user = html.escape(username)

        if dias_restantes > 0:
            mensaje += f"• {safe_user} (ID: <code>{user_id}</code>): le quedan <b>{dias_restantes} días</b>\n"
        else:
            mensaje += f"• {safe_user} (ID: <code>{user_id}</code>): ❌ <b>Caducada</b>\n"

    await update.message.reply_html(mensaje)

# Tarea automática que revisa cada día si caducan subs
async def comprobar_caducidades_diarias(context: ContextTypes.DEFAULT_TYPE):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, fecha_fin FROM subs")
    rows = cursor.fetchall()
    conn.close()

    hoy = datetime.datetime.now().date()
    admins_str = " ".join([html.escape(a) for a in ADMINS])

    for user_id, username, fecha_str in rows:
        fecha_fin = datetime.datetime.fromisoformat(fecha_str).date()
        
        # Si finaliza justo hoy
        if fecha_fin == hoy:
            dias_totales = (datetime.datetime.fromisoformat(fecha_str) - datetime.datetime.now()).days + 1
            if dias_totales <= 0:
                dias_totales = 1

            safe_user = html.escape(username)
            mensaje = (
                f"₍˶ᵔ ˕ ᵔ˶₎  𝓗ey admins! {admins_str}\n"
                f"la sub de {safe_user} de {dias_totales} días finaliza hoy ¡no olviden preguntar por su renovación!"
            )
            await context.bot.send_message(chat_id=AVISOS_CHAT_ID, text=mensaje, parse_mode="HTML")

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
