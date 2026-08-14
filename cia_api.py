"""
cia_api.py
==========

Proyecto: CIA Triad Demo API
Autor: Citlali Guzman
Descripción: API que demuestra los principios de confidencialidad, integridad y disponibilidad

C - Confidencialidad: cifra y descifra mensajes
I - Integridad: firma y verifica mensajes
A - Disponibilidad: simula servidores redundantes

Ejecución:
    pip install fastapi "uvicorn[standard]" cryptography
    uvicorn cia_api:app --reload

Documentación:
    http://127.0.0.1:8000/docs
"""

import hashlib
import hmac
import os
import random

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from cryptography.fernet import Fernet, InvalidToken


# Crea la aplicación principal con FastAPI
app = FastAPI(
    title="CIA Triad Demo API",
    description="API de ejemplo para demostrar Confidencialidad, Integridad y Disponibilidad",
    version="1.0.0",
)


# CLAVES DE SEGURIDAD

# Genera una clave utilizada para cifrar y descifrar mensajes
ENCRYPTION_KEY = Fernet.generate_key()

# Crea el objeto encargado de realizar el cifrado
_cipher = Fernet(ENCRYPTION_KEY)

# Genera una clave utilizada para firmar y verificar mensajes
SIGNING_KEY = os.urandom(32)


# SERVIDORES SIMULADOS PARA DISPONIBILIDAD

# Lista de servidores utilizados en la simulación
NODES = ["server-1", "server-2", "server-3"]

# Probabilidad de que cada servidor se encuentre disponible
NODE_RELIABILITY = 0.55


# C - CONFIDENCIALIDAD

# Modelo del mensaje que será cifrado
class EncryptRequest(BaseModel):
    message: str


# Modelo de respuesta que contiene el mensaje cifrado
class EncryptResponse(BaseModel):
    ciphertext: str


# Modelo utilizado para recibir un mensaje cifrado
class DecryptRequest(BaseModel):
    ciphertext: str


# Modelo de respuesta que contiene el texto descifrado
class DecryptResponse(BaseModel):
    plaintext: str


# CIFRAR MENSAJE

@app.post(
    "/confidentiality/encrypt",
    response_model=EncryptResponse,
    tags=["Confidentiality"],
)
def encrypt(payload: EncryptRequest):

    # Convierte el mensaje en bytes y lo cifra utilizando Fernet
    token = _cipher.encrypt(payload.message.encode())

    # Devuelve el mensaje cifrado como texto
    return EncryptResponse(
        ciphertext=token.decode()
    )


# DESCIFRAR MENSAJE

@app.post(
    "/confidentiality/decrypt",
    response_model=DecryptResponse,
    tags=["Confidentiality"],
)
def decrypt(payload: DecryptRequest):

    try:
        # Intenta descifrar el ciphertext utilizando la clave del servidor
        plaintext = _cipher.decrypt(
            payload.ciphertext.encode()
        )

    except InvalidToken:
        # Rechaza el mensaje si el ciphertext no es válido
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid ciphertext or wrong key — access denied",
        )

    # Devuelve el mensaje original en texto plano
    return DecryptResponse(
        plaintext=plaintext.decode()
    )


# I - INTEGRIDAD

# Modelo del mensaje que será firmado
class SignRequest(BaseModel):
    message: str


# Modelo de respuesta que contiene el mensaje y su firma
class SignResponse(BaseModel):
    message: str
    signature: str


# Modelo utilizado para verificar un mensaje y su firma
class VerifyRequest(BaseModel):
    message: str
    signature: str


# Modelo de respuesta con el resultado de la verificación
class VerifyResponse(BaseModel):
    valid: bool


# GENERAR FIRMA

def _sign(message: str) -> str:

    # Genera una firma HMAC-SHA256 utilizando la clave del servidor
    return hmac.new(
        SIGNING_KEY,
        message.encode(),
        hashlib.sha256,
    ).hexdigest()


# FIRMAR MENSAJE

@app.post(
    "/integrity/sign",
    response_model=SignResponse,
    tags=["Integrity"],
)
def sign(payload: SignRequest):

    # Genera una firma para comprobar posteriormente la integridad
    signature = _sign(payload.message)

    # Devuelve el mensaje original junto con su firma
    return SignResponse(
        message=payload.message,
        signature=signature,
    )


# VERIFICAR INTEGRIDAD

@app.post(
    "/integrity/verify",
    response_model=VerifyResponse,
    tags=["Integrity"],
)
def verify(payload: VerifyRequest):

    # Genera nuevamente la firma esperada del mensaje recibido
    expected = _sign(payload.message)

    # Compara la firma recibida con la firma correcta
    is_valid = hmac.compare_digest(
        expected,
        payload.signature,
    )

    # Devuelve True si el mensaje conserva su integridad
    return VerifyResponse(
        valid=is_valid
    )


# A - DISPONIBILIDAD

# Modelo que representa el estado de un servidor
class NodeStatus(BaseModel):
    name: str
    status: str


# Modelo de respuesta con todos los servidores
class StatusResponse(BaseModel):
    nodes: list[NodeStatus]


# Modelo que indica qué servidor atendió la solicitud
class RequestResponse(BaseModel):
    served_by: str


# CONSULTAR ESTADO DE LOS SERVIDORES

@app.get(
    "/availability/status",
    response_model=StatusResponse,
    tags=["Availability"],
)
def availability_status():

    # Simula si cada servidor se encuentra activo o inactivo
    nodes = [
        NodeStatus(
            name=n,
            status="UP"
            if random.random() < NODE_RELIABILITY
            else "DOWN",
        )
        for n in NODES
    ]

    # Devuelve el estado actual de todos los servidores
    return StatusResponse(
        nodes=nodes
    )


# SIMULAR DISPONIBILIDAD DEL SERVICIO

@app.get(
    "/availability/request",
    response_model=RequestResponse,
    tags=["Availability"],
)
def availability_request():

    # Recorre los servidores hasta encontrar uno disponible
    for node in NODES:

        # Simula si el servidor puede atender la solicitud
        if random.random() < NODE_RELIABILITY:

            # Devuelve el nombre del servidor que respondió
            return RequestResponse(
                served_by=node
            )

    # Devuelve error 503 si todos los servidores están inactivos
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="All redundant nodes are down — service unavailable",
    )


# RUTA PRINCIPAL

@app.get("/", tags=["Root"])
def root():

    # Muestra información general y las rutas disponibles
    return {
        "message": "CIA Triad Demo API — open /docs to try each endpoint interactively",
        "principles": {
            "confidentiality":
                "/confidentiality/encrypt, /confidentiality/decrypt",

            "integrity":
                "/integrity/sign, /integrity/verify",

            "availability":
                "/availability/status, /availability/request",
        },
    }