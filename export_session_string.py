from telethon.sessions import SQLiteSession, StringSession


def main() -> None:
    session = SQLiteSession("session")

    if not session.auth_key:
        raise SystemExit(
            "No se encontro una sesion autenticada en session.session. "
            "Primero ejecuta app.py en local y completa el login."
        )

    print(StringSession.save(session))


if __name__ == "__main__":
    main()