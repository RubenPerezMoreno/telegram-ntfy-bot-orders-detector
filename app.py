import asyncio
import builtins
import os
import re
from datetime import datetime
from threading import Lock, Thread

import requests
from flask import Flask, render_template_string
from telethon import TelegramClient, events
from telethon.errors.common import TypeNotFoundError
from telethon.errors.rpcerrorlist import AuthKeyDuplicatedError
from telethon.sessions import StringSession

# =========================
# CONFIG
# =========================

api_id_raw = os.environ.get("api_id")
api_hash = os.environ.get("api_hash")
topic = os.environ.get("topic")

channel_id_raw = os.environ.get("channel_id")

PORT = int(os.environ.get("PORT", "8000"))
LOG_FILE = os.environ.get("LOG_FILE", "app.log")

# =========== CONFIG PRE RENDER ==========

# api_id_raw = 
# api_hash = ''

# topic = ""

# channel_id_raw = 

# PORT = int(os.environ.get("PORT", "8000"))
# LOG_FILE = os.environ.get("LOG_FILE", "app.log")

# =========================
# VALIDACIÓN VARIABLES
# =========================

if not api_id_raw:
    raise Exception("api_id no configurado")

if not api_hash:
    raise Exception("api_hash no configurado")

if not topic:
    raise Exception("topic no configurado")

if not channel_id_raw:
    raise Exception("channel_id no configurado")

api_id = int(api_id_raw)


def parse_channel_ids(raw_value):
    values = [item.strip() for item in raw_value.replace(";", ",").split(",") if item.strip()]
    if not values:
        raise Exception("channel_id no configurado")

    parsed = []
    for value in values:
        try:
            parsed.append(int(value))
        except ValueError as exc:
            raise Exception(f"channel_id inválido: {value}") from exc

    return parsed


channel_ids = parse_channel_ids(channel_id_raw)
channel_id = channel_ids[0] if len(channel_ids) == 1 else channel_ids

# TRUE = filtra solo señales esperadas
# FALSE = reenvia todos los mensajes del canal configurado
FILTER_MESSAGES = os.environ.get("FILTER_MESSAGES", "true").strip().lower() in {"1", "true", "yes", "on"}

# =========================
# CLIENT
# =========================

session_string = os.environ.get("TELETHON_SESSION_STRING")
running_on_render = os.environ.get("RENDER") == "true" or "RENDER_SERVICE_ID" in os.environ

if session_string:
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
else:
    client = TelegramClient('session', api_id, api_hash)
app = Flask(__name__)

if running_on_render and not session_string:
    raise RuntimeError(
        "TELETHON_SESSION_STRING no esta configurado en Render. "
        "Genera la StringSession en local y guardala como variable de entorno."
    )

# EVITAR DUPLICADOS
mensajes_procesados = set()
log_lock = Lock()

log_dir = os.path.dirname(LOG_FILE)
if log_dir:
    os.makedirs(log_dir, exist_ok=True)


def read_log_lines():
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as log_file:
            return [line.rstrip("\n") for line in log_file]
    except FileNotFoundError:
        return []
    except Exception as exc:
        return [f"[ERROR] No se pudo leer {LOG_FILE}: {exc}"]


def log(*args, sep=" ", end="\n", flush=False):
    message = sep.join(str(arg) for arg in args)
    builtins.print(message, end=end, flush=flush)

    timestamp = datetime.now().strftime("%H:%M:%S")
    lines = message.splitlines() or [""]

    with log_lock:
        with open(LOG_FILE, "a", encoding="utf-8") as log_file:
            for line in lines:
                log_file.write(f"[{timestamp}] {line}\n")


print = log


@app.get("/")
def home():
    with log_lock:
        logs = read_log_lines()

    return render_template_string(
        """
        <!doctype html>
        <html lang="es">
        <head>
            <meta charset="utf-8">
            <meta http-equiv="refresh" content="3">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Telegram NTFY Bot</title>
            <style>
                :root {
                    color-scheme: dark;
                    --bg: #0b1020;
                    --panel: #121a33;
                    --border: #24304f;
                    --text: #e7ecff;
                    --muted: #9aa6c8;
                    --accent: #7dd3fc;
                }
                body {
                    margin: 0;
                    font-family: Arial, sans-serif;
                    background: linear-gradient(180deg, #0b1020 0%, #101935 100%);
                    color: var(--text);
                    min-height: 100vh;
                    overflow: hidden;
                }
                .wrap {
                    max-width: 1100px;
                    margin: 0 auto;
                    padding: 32px 24px;
                    height: 100vh;
                    box-sizing: border-box;
                    display: flex;
                }
                .card {
                    background: rgba(18, 26, 51, 0.92);
                    border: 1px solid var(--border);
                    border-radius: 16px;
                    padding: 24px 24px 20px;
                    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
                    height: 100%;
                    min-height: 0;
                    width: 100%;
                    display: flex;
                    flex-direction: column;
                    gap: 10px;
                }
                h1 {
                    margin: 0;
                    font-size: 28px;
                }
                .meta {
                    color: var(--muted);
                    margin-bottom: 4px;
                }
                pre {
                    margin: 4px 0 0;
                    padding: 16px;
                    background: #09101f;
                    border: 1px solid var(--border);
                    border-radius: 12px;
                    white-space: pre-wrap;
                    word-break: break-word;
                    flex: 1;
                    min-height: 0;
                    overflow: auto;
                }
                .empty {
                    color: var(--muted);
                }
                .badge {
                    display: inline-flex;
                    align-self: flex-start;
                    padding: 4px 10px;
                    border-radius: 999px;
                    background: rgba(125, 211, 252, 0.12);
                    color: var(--accent);
                    border: 1px solid rgba(125, 211, 252, 0.28);
                    font-size: 12px;
                    margin-bottom: 0;
                }
            </style>
        </head>
        <body>
            <div class="wrap">
                <div class="card">
                    <div class="badge">Web Service activo</div>
                    <h1>Logs de la aplicacion</h1>
                    <div class="meta">La pagina se actualiza sola cada 3 segundos.</div>
                    <pre>{% if logs %}{{ logs|join('\n') }}{% else %}<span class="empty">Aun no hay logs.</span>{% endif %}</pre>
                </div>
            </div>
        </body>
        </html>
        """,
        logs=logs,
    )


@app.get("/healthz")
def healthz():
    return {"status": "healthy"}

# =========================
# REGEX PRINCIPAL
# =========================

PATRON_SENAL = re.compile(
    r"Nueva operación:\s*[A-Z0-9._/-]+\s*-\s*(Buy|Sell)",
    re.IGNORECASE
)

# =========================
# HANDLER
# =========================

@client.on(events.NewMessage(chats=channel_ids))
async def handler(event):

    print("\n============================")
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

    if FILTER_MESSAGES:
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

        mensaje_a_enviar = match.group(1).strip()

        print("\n==============================")
        print("SEÑAL DETECTADA")
        print("==============================")

        print("\nMENSAJE FILTRADO:")
        print(mensaje_a_enviar)
    else:
        print("Filtro de mensajes desactivado -> reenviando mensaje completo")
        mensaje_a_enviar = mensaje or "(sin texto)"

        print("\nMENSAJE A ENVIAR:")
        print(mensaje_a_enviar)

    # =========================
    # NOTIFICACION
    # =========================

    notificacion = f"""
🚨 NUEVA SEÑAL 🚨

{mensaje_a_enviar}
"""

    # =========================
    # ENVIAR NTFY
    # =========================

    try:

        r = requests.post(
            f"https://ntfy.sh/{topic}",
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
print(f"ESCUCHANDO CANAL(ES): {channel_ids}")
print("===================================\n")


def run_web_server():
    app.run(host="0.0.0.0", port=PORT)


Thread(target=run_web_server, daemon=True).start()

async def run_client():
    while True:
        try:
            if session_string:
                await client.connect()

                if not await client.is_user_authorized():
                    raise RuntimeError(
                        "TELETHON_SESSION_STRING es invalida o ya no esta autorizada. "
                        "Regenera la sesion desde local."
                    )
            else:
                await client.start()

            await client.run_until_disconnected()
            break
        except AuthKeyDuplicatedError:
            print("ERROR TELEGRAM: la sesion esta siendo usada desde otra IP al mismo tiempo")
            print("Deten la otra instancia o genera una TELETHON_SESSION_STRING nueva solo para Render")
            print("Reintentando conexion en 60 segundos...")

            try:
                await client.disconnect()
            except Exception:
                pass

            await asyncio.sleep(60)
        except TypeNotFoundError as exc:
            print("ERROR TELETHON: constructor TL desconocido al procesar updates")
            print(str(exc))
            print("Reintentando con una nueva conexión en 5 segundos...")

            try:
                await client.disconnect()
            except Exception:
                pass

            await asyncio.sleep(5)


asyncio.run(run_client())
