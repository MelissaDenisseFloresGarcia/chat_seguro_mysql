# Chat Seguro con CIA API + MySQL

Proyecto web que cumple la práctica de cifrado y verificación de integridad.

## Componentes

- `cia_api.py`: API original proporcionada.
- `chat_app.py`: backend del chat.
- `index.html`: cliente web.
- `config.py`: datos de conexión a MySQL.
- `schema.sql`: creación de base de datos y tabla.
- `requirements.txt`: dependencias.

## 1. Crear la base de datos

Abre MySQL Workbench.

Conéctate a tu servidor local y abre una pestaña SQL.

Abre `schema.sql`, o copia su contenido, y ejecútalo.

Debe crear:

- Base de datos: `chat_seguro`
- Tabla: `messages`

## 2. Configurar contraseña

Abre `config.py`.

Cambia:

```python
MYSQL_PASSWORD = "PON_AQUI_TU_PASSWORD"
```

por tu contraseña de MySQL.

Ejemplo:

```python
MYSQL_PASSWORD = "MiClave123"
```

## 3. Crear entorno virtual

En una terminal dentro de la carpeta:

```cmd
python -m venv venv
```

Activa el entorno en CMD:

```cmd
venv\Scripts\activate
```

En PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

## 4. Instalar dependencias

```cmd
pip install -r requirements.txt
```

## 5. Ejecutar CIA API

Terminal 1:

```cmd
uvicorn cia_api:app --reload --port 8000
```

Prueba:

http://127.0.0.1:8000/docs

## 6. Ejecutar el chat

Abre otra terminal en la misma carpeta.

Activa nuevamente el entorno virtual:

```cmd
venv\Scripts\activate
```

Después:

```cmd
uvicorn chat_app:app --reload --port 8001
```

Abre:

http://127.0.0.1:8001

## 7. Probar los dos usuarios

Abre dos pestañas del navegador.

Pestaña 1:
- Usuario A

Pestaña 2:
- Usuario B

Envía mensajes desde ambas.

## Flujo

1. El usuario escribe un mensaje.
2. `chat_app.py` llama por HTTP a `/confidentiality/encrypt`.
3. Llama por HTTP a `/integrity/sign`.
4. Guarda `ciphertext`, `signature`, remitente, destinatario y timestamp en MySQL.
5. Para desplegar el chat ejecuta un `SELECT` en MySQL.
6. Cada mensaje recuperado se descifra mediante `/confidentiality/decrypt`.
7. Se muestra primero `No verificado`.
8. Después el navegador solicita la verificación.
9. `chat_app.py` llama a `/integrity/verify`.
10. Si devuelve `valid: true`, se muestra `Mensaje verificado`.

## Comprobar la base de datos

En MySQL Workbench:

```sql
USE chat_seguro;

SELECT * FROM messages;
```

La columna `ciphertext` debe contener el mensaje cifrado y NO el texto plano.

## Nota importante

La CIA API original genera nuevas claves cuando se reinicia.

Por ese motivo, durante una demostración no reinicies `cia_api.py`
después de enviar mensajes. Si la reinicias, las claves anteriores dejan
de servir para descifrar los mensajes guardados anteriormente.

Para comenzar una prueba limpia:

```sql
USE chat_seguro;
TRUNCATE TABLE messages;
```
