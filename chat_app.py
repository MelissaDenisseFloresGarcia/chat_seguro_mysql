from pathlib import Path
from datetime import datetime

import mysql.connector
import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from config import (
    MYSQL_HOST,
    MYSQL_PORT,
    MYSQL_USER,
    MYSQL_PASSWORD,
    MYSQL_DATABASE,
)

app = FastAPI(title="Chat Seguro Web con MySQL")

# CIA API proporcionada por el profesor
CIA_API_URL = "http://127.0.0.1:8000"

# Página web del chat
HTML_PATH = Path(__file__).with_name("index.html")


# ============================================================
# CONEXIÓN A MYSQL
# ============================================================
def get_connection():
    """
    Abre una conexión con la base de datos MySQL.
    Los datos de conexión se encuentran en config.py.
    """
    try:
        return mysql.connector.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,
        )
    except mysql.connector.Error as error:
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo conectar con MySQL: {error}",
        )


# ============================================================
# MODELO PARA RECIBIR UN MENSAJE DEL NAVEGADOR
# ============================================================
class MessageCreate(BaseModel):
    sender: str
    receiver: str
    message: str


# ============================================================
# PÁGINA PRINCIPAL
# ============================================================
@app.get("/", response_class=HTMLResponse)
def home():
    return HTML_PATH.read_text(encoding="utf-8")


# ============================================================
# ENVIAR UN MENSAJE
# ============================================================
@app.post("/messages")
def send_message(payload: MessageCreate):
    """
    Flujo del envío:
    1. Cifrar el texto con CIA API.
    2. Firmar el texto con CIA API.
    3. Guardar cifrado + firma + remitente + destinatario + fecha en MySQL.
    """

    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="El mensaje está vacío.")

    # --------------------------------------------------------
    # 1. CIFRADO
    # POST /confidentiality/encrypt
    # --------------------------------------------------------
    try:
        encrypt_response = requests.post(
            f"{CIA_API_URL}/confidentiality/encrypt",
            json={"message": payload.message},
            timeout=5,
        )
        encrypt_response.raise_for_status()
    except requests.RequestException as error:
        raise HTTPException(
            status_code=503,
            detail=f"No se pudo contactar la CIA API para cifrar: {error}",
        )

    ciphertext = encrypt_response.json()["ciphertext"]

    # --------------------------------------------------------
    # 2. FIRMA
    # POST /integrity/sign
    # --------------------------------------------------------
    try:
        sign_response = requests.post(
            f"{CIA_API_URL}/integrity/sign",
            json={"message": payload.message},
            timeout=5,
        )
        sign_response.raise_for_status()
    except requests.RequestException as error:
        raise HTTPException(
            status_code=503,
            detail=f"No se pudo contactar la CIA API para firmar: {error}",
        )

    signature = sign_response.json()["signature"]
    timestamp = datetime.now()

    # --------------------------------------------------------
    # 3. GUARDAR EN MYSQL
    # IMPORTANTE: NO guardamos el texto plano.
    # --------------------------------------------------------
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO messages
                (sender, receiver, ciphertext, signature, timestamp)
            VALUES
                (%s, %s, %s, %s, %s)
            """,
            (
                payload.sender,
                payload.receiver,
                ciphertext,
                signature,
                timestamp,
            ),
        )
        conn.commit()
        message_id = cursor.lastrowid
    finally:
        cursor.close()
        conn.close()

    return {
        "ok": True,
        "id": message_id,
        "message": "Mensaje cifrado, firmado y guardado en MySQL.",
    }


# ============================================================
# LEER LOS MENSAJES DESDE MYSQL
# ============================================================
@app.get("/messages")
def get_messages():
    """
    Los mensajes NO se toman de memoria.
    Primero se consultan desde MySQL y luego cada ciphertext
    se envía a la CIA API para descifrarlo.
    """

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                id,
                sender,
                receiver,
                ciphertext,
                signature,
                timestamp
            FROM messages
            ORDER BY id ASC
            """
        )
        rows = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    result = []

    for row in rows:
        # ----------------------------------------------------
        # 4. DESCIFRADO
        # POST /confidentiality/decrypt
        # ----------------------------------------------------
        try:
            decrypt_response = requests.post(
                f"{CIA_API_URL}/confidentiality/decrypt",
                json={"ciphertext": row["ciphertext"]},
                timeout=5,
            )

            if decrypt_response.ok:
                plaintext = decrypt_response.json()["plaintext"]
            else:
                plaintext = "[No se pudo descifrar]"
        except requests.RequestException:
            plaintext = "[CIA API no disponible]"

        result.append(
            {
                "id": row["id"],
                "sender": row["sender"],
                "receiver": row["receiver"],
                # Solo se devuelve al navegador el texto ya descifrado.
                "message": plaintext,
                "timestamp": row["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
                # El navegador debe mostrarlo primero como No verificado.
                "verified": False,
            }
        )

    return result


# ============================================================
# VERIFICAR LA INTEGRIDAD DE UN MENSAJE
# ============================================================
@app.post("/messages/{message_id}/verify")
def verify_message(message_id: int):
    """
    1. Recupera ciphertext y signature DESDE MySQL.
    2. Descifra el ciphertext.
    3. Envía plaintext + signature a POST /integrity/verify.
    """

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT ciphertext, signature
            FROM messages
            WHERE id = %s
            """,
            (message_id,),
        )
        row = cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado.")

    # Desciframos lo recuperado de la base de datos.
    try:
        decrypt_response = requests.post(
            f"{CIA_API_URL}/confidentiality/decrypt",
            json={"ciphertext": row["ciphertext"]},
            timeout=5,
        )
    except requests.RequestException as error:
        raise HTTPException(
            status_code=503,
            detail=f"No se pudo contactar la CIA API: {error}",
        )

    if not decrypt_response.ok:
        return {"valid": False}

    plaintext = decrypt_response.json()["plaintext"]

    # --------------------------------------------------------
    # 5. VERIFICACIÓN DE INTEGRIDAD
    # POST /integrity/verify
    # --------------------------------------------------------
    try:
        verify_response = requests.post(
            f"{CIA_API_URL}/integrity/verify",
            json={
                "message": plaintext,
                "signature": row["signature"],
            },
            timeout=5,
        )
        verify_response.raise_for_status()
    except requests.RequestException as error:
        raise HTTPException(
            status_code=503,
            detail=f"No se pudo verificar el mensaje: {error}",
        )

    return {
        "valid": verify_response.json()["valid"]
    }
