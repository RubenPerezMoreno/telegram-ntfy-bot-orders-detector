from telethon import TelegramClient, events
import requests
import re
import os

# =========================
# CONFIG
# =========================

api_id = int(os.environ.get("api_id"))
api_hash = os.environ.get("api_hash")

TOPIC = os.environ.get("TOPIC")

CHANNEL_ID = int(os.environ.get("CHANNEL_ID"))

# =========================
# VALIDACIÓN VARIABLES
# =========================

if not api_id:
    raise Exception("api_id no configurado")

if not api_hash:
    raise Exception("api_hash no configurado")

if not TOPIC:
    raise Exception("TOPIC no configurado")

if not CHANNEL_ID:
    raise Exception("CHANNEL_ID no configurado")

# =========================
# CLIENT
# =========================

client = TelegramClient('session', api_id, api_hash)

# EVITAR DUPLICADOS
mensajes_procesados = set()

# =========================
# REGEX PRINCIPAL
# =========================

PATRON_SENAL = re.compile(
    r"Nueva operación:\s*XAUUSD\s*-\s*(Buy|Sell)",
    re.IGNORECASE
)

# =========================
# HANDLER
# =========================

@client.on(events.NewMessage(chats=CHANNEL_ID))
async def handler(event):

    print("\n==============================")
    print("MENSAJE RECIBIDO")
    print("==============================")

    print("Chat ID:", event.chat_id)
    print("Event ID:", event.id)

    # =========================
    # EVITAR DUPLICADOS
    # =========================

    if event.id in mensajes_procesados:
        print("Mensaje duplicado ignorado")
        return

    mensajes_procesados.add(event.id)

    # =========================
    # CONTENIDO MENSAJE
    # =========================

    mensaje = event.raw_text.strip()

    print("\nCONTENIDO ORIGINAL:")
    print(mensaje)

    # =========================
    # VALIDACIONES
    # =========================

    if not PATRON_SENAL.search(mensaje):
        print("Mensaje ignorado -> No contiene patrón principal")
        return

    if not ("Buy" in mensaje or "Sell" in mensaje):
        print("Mensaje ignorado -> No contiene Buy/Sell")
        return

    if "Punto de entrada" not in mensaje:
        print("Mensaje ignorado -> Falta Punto de entrada")
        return

    if "Stop Loss" not in mensaje:
        print("Mensaje ignorado -> Falta Stop Loss")
        return

    # =========================
    # VALIDAR TPS
    # =========================

    tps = re.findall(r"- TP\d+", mensaje)

    print("\nTPS DETECTADOS:")
    print(tps)

    # Deben existir EXACTAMENTE 10 TPs
    if len(tps) != 10:
        print(f"Mensaje ignorado -> Numero incorrecto de TPs ({len(tps)})")
        return

    # Deben ser EXACTAMENTE TP1 a TP10
    tps_esperados = [
        "- TP1", "- TP2", "- TP3", "- TP4", "- TP5",
        "- TP6", "- TP7", "- TP8", "- TP9", "- TP10"
    ]

    if tps != tps_esperados:
        print("Mensaje ignorado -> Los TPs no coinciden exactamente")

        print("Esperados:")
        print(tps_esperados)

        print("Recibidos:")
        print(tps)

        return

    # =========================
    # EXTRAER SOLO LA SEÑAL
    # =========================

    match = re.search(
        r"(🏆 Nueva operación:.*?🛑 Stop Loss fijado en .*?)(?:\n|$)",
        mensaje,
        re.DOTALL
    )

    if not match:
        print("Mensaje ignorado -> No se pudo extraer la señal")
        return

    mensaje_filtrado = match.group(1).strip()

    print("\n==============================")
    print("SEÑAL DETECTADA")
    print("==============================")

    print("\nMENSAJE FILTRADO:")
    print(mensaje_filtrado)

    # =========================
    # NOTIFICACION
    # =========================

    notificacion = f"""
🚨 NUEVA SEÑAL 🚨

{mensaje_filtrado}
"""

    # =========================
    # ENVIAR NTFY
    # =========================

    try:

        r = requests.post(
            f"https://ntfy.sh/{TOPIC}",
            data=notificacion.encode("utf-8"),
            headers={
                "X-Title": "",
                "Priority": "urgent",
                "Tags": "telegram"
            }
        )

        print("\n==============================")
        print("SEÑAL REENVIADO")
        print("==============================")

        print("STATUS:", r.status_code)
        print("\n", r.text)

    except Exception as e:


        print("\n==============================")
        print("ERROR EN ENVIO")
        print("==============================")

        print(str(e))


# =========================
# START
# =========================

print("\n===================================")
print("BOT INICIADO")
print("ESCUCHANDO CANAL...")
print("===================================\n")

client.start()
client.run_until_disconnected()


# =========================================
# WEB SERVER - Port Binding for Render.com
# =========================================

from flask import Flask

app = Flask(__name__)

@app.route("/")
def index():
    return "Bot is running"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)

# =========================
