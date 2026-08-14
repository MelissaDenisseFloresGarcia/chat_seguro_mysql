from pathlib import Path
from datetime import datetime

import mysql.connector
import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# Importa los datos necesarios para conectarse a MySQL
from config import (
    MYSQL_HOST,
    MYSQL_PORT,
    MYSQL_USER,
    MYSQL_PASSWORD,
    MYSQL_DATABASE,
)

# Crea la aplicación web utilizando FastAPI
app = FastAPI(title="Chat Seguro Web con MySQL")

# Dirección donde se ejecuta la CIA API proporcionada por el profesor
CIA_API_URL = "http://127.0.0.1:8000"

# Localiza el archivo HTML que contiene la interfaz del chat
HTML_PATH = Path(__file__).with_name("index.html")


# CONEXIÓN A MYSQL

def get_connection():
    """Realiza la conexión entre la aplicación y la base de datos MySQL."""

    try:
        # Abre la conexión usando los datos definidos en config.py
        return mysql.connector.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,
        )

    except mysql.connector.Error as error:
        # Muestra un error si no es posible conectarse a MySQL
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo conectar con MySQL: {error}",
        )


# MODELO DEL MENSAJE

class MessageCreate(BaseModel):
    # Nombre del usuario que envía el mensaje
    sender: str

    # Nombre del usuario que recibe el mensaje
    receiver: str

    # Texto escrito por el usuario
    message: str


# PÁGINA PRINCIPAL

@app.get("/", response_class=HTMLResponse)
def home():
    # Carga index.html cuando el usuario entra al chat
    return HTML_PATH.read_text(encoding="utf-8")


# ENVIAR MENSAJE

@app.post("/messages")
def send_message(payload: MessageCreate):

    # Evita que se puedan enviar mensajes vacíos
    if not payload.message.strip():
        raise HTTPException(
            status_code=400,
            detail="El mensaje está vacío."
        )


    # 1. CIFRADO DEL MENSAJE

    try:
        # Envía el texto a la CIA API para cifrarlo antes de guardarlo
        encrypt_response = requests.post(
            f"{CIA_API_URL}/confidentiality/encrypt",
            json={"message": payload.message},
            timeout=5,
        )

        # Comprueba que la CIA API respondió correctamente
        encrypt_response.raise_for_status()

    except requests.RequestException as error:
        # Informa si ocurrió un problema durante el cifrado
        raise HTTPException(
            status_code=503,
            detail=f"No se pudo contactar la CIA API para cifrar: {error}",
        )

    # Obtiene únicamente el mensaje cifrado devuelto por la CIA API
    ciphertext = encrypt_response.json()["ciphertext"]


    # 2. FIRMA DEL MENSAJE

    try:
        # Envía el mensaje a la CIA API para generar su firma de integridad
        sign_response = requests.post(
            f"{CIA_API_URL}/integrity/sign",
            json={"message": payload.message},
            timeout=5,
        )

        # Comprueba que la firma fue generada correctamente
        sign_response.raise_for_status()

    except requests.RequestException as error:
        # Informa si ocurrió un problema al generar la firma
        raise HTTPException(
            status_code=503,
            detail=f"No se pudo contactar la CIA API para firmar: {error}",
        )

    # Obtiene la firma generada por la CIA API
    signature = sign_response.json()["signature"]

    # Guarda la fecha y hora en que se envió el mensaje
    timestamp = datetime.now()


    # 3. GUARDADO DEL MENSAJE EN MYSQL

    # Abre una conexión con la base de datos
    conn = get_connection()

    # Crea un cursor para ejecutar instrucciones SQL
    cursor = conn.cursor()

    try:
        # Guarda el mensaje cifrado y su firma sin guardar el texto original
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

        # Confirma el guardado del mensaje en MySQL
        conn.commit()

        # Obtiene el identificador del mensaje recién creado
        message_id = cursor.lastrowid

    finally:
        # Cierra el cursor después de utilizarlo
        cursor.close()

        # Cierra la conexión con MySQL
        conn.close()

    # Devuelve una respuesta indicando que el mensaje fue guardado
    return {
        "ok": True,
        "id": message_id,
        "message": "Mensaje cifrado, firmado y guardado en MySQL.",
    }


# CONSULTAR MENSAJES

@app.get("/messages")
def get_messages():

    # Abre una conexión con MySQL
    conn = get_connection()

    # Permite obtener las columnas de MySQL como un diccionario
    cursor = conn.cursor(dictionary=True)

    try:
        # Consulta todos los mensajes directamente desde la base de datos
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

        # Obtiene todos los mensajes encontrados
        rows = cursor.fetchall()

    finally:
        # Cierra el cursor después de realizar la consulta
        cursor.close()

        # Cierra la conexión con MySQL
        conn.close()

    # Aquí se almacenan temporalmente los mensajes que se mostrarán en el chat
    result = []

    # Recorre uno por uno los mensajes obtenidos desde MySQL
    for row in rows:


        # 4. DESCIFRADO DEL MENSAJE

        try:
            # Envía el ciphertext almacenado a la CIA API para descifrarlo
            decrypt_response = requests.post(
                f"{CIA_API_URL}/confidentiality/decrypt",
                json={"ciphertext": row["ciphertext"]},
                timeout=5,
            )

            # Obtiene el texto original solamente si el descifrado fue correcto
            if decrypt_response.ok:
                plaintext = decrypt_response.json()["plaintext"]
            else:
                plaintext = "[No se pudo descifrar]"

        except requests.RequestException:
            # Muestra este texto si la CIA API no está disponible
            plaintext = "[CIA API no disponible]"

        # Prepara el mensaje descifrado para enviarlo al navegador
        result.append(
            {
                "id": row["id"],
                "sender": row["sender"],
                "receiver": row["receiver"],

                # El usuario solamente puede ver el mensaje ya descifrado
                "message": plaintext,

                # Convierte la fecha a un formato fácil de leer
                "timestamp": row["timestamp"].strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),

                # Todos los mensajes aparecen primero como No verificado
                "verified": False,
            }
        )

    # Envía al navegador los mensajes obtenidos desde MySQL
    return result

# VERIFICACIÓN DE INTEGRIDAD

@app.post("/messages/{message_id}/verify")
def verify_message(message_id: int):

    # Abre una conexión con MySQL
    conn = get_connection()

    # Permite consultar las columnas utilizando su nombre
    cursor = conn.cursor(dictionary=True)

    try:
        # Recupera de MySQL el ciphertext y la firma del mensaje seleccionado
        cursor.execute(
            """
            SELECT ciphertext, signature
            FROM messages
            WHERE id = %s
            """,
            (message_id,),
        )

        # Obtiene el mensaje encontrado
        row = cursor.fetchone()

    finally:
        # Cierra el cursor
        cursor.close()

        # Cierra la conexión con la base de datos
        conn.close()

    # Devuelve un error si el mensaje solicitado no existe
    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Mensaje no encontrado."
        )


    # DESCIFRADO PARA REALIZAR LA VERIFICACIÓN

    try:
        # Descifra nuevamente el mensaje recuperado desde MySQL
        decrypt_response = requests.post(
            f"{CIA_API_URL}/confidentiality/decrypt",
            json={"ciphertext": row["ciphertext"]},
            timeout=5,
        )

    except requests.RequestException as error:
        # Informa si no fue posible comunicarse con la CIA API
        raise HTTPException(
            status_code=503,
            detail=f"No se pudo contactar la CIA API: {error}",
        )

    # Si el mensaje no puede descifrarse se considera inválido
    if not decrypt_response.ok:
        return {"valid": False}

    # Obtiene el texto original después de descifrarlo
    plaintext = decrypt_response.json()["plaintext"]


    # 5. VERIFICACIÓN DE INTEGRIDAD

    try:
        # Envía el mensaje y su firma a la CIA API para comprobar su integridad
        verify_response = requests.post(
            f"{CIA_API_URL}/integrity/verify",
            json={
                "message": plaintext,
                "signature": row["signature"],
            },
            timeout=5,
        )

        # Comprueba que la CIA API respondió correctamente
        verify_response.raise_for_status()

    except requests.RequestException as error:
        # Informa si ocurrió un problema durante la verificación
        raise HTTPException(
            status_code=503,
            detail=f"No se pudo verificar el mensaje: {error}",
        )

    # Devuelve True si el mensaje conserva su integridad y False si fue alterado
    return {
        "valid": verify_response.json()["valid"]
    }