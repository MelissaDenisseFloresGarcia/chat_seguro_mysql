# Chat Seguro con CIA API + MySQL

**Alumno:** Melissa Denisse Flores García

Este proyecto consiste en un chat web entre dos usuarios que utiliza la CIA API proporcionada para proteger los mensajes mediante cifrado y verificación de integridad

Los mensajes enviados se cifran y firman antes de guardarse en MySQL. Cuando se muestran en el chat, se leen desde la base de datos, se descifran y posteriormente se verifica que no hayan sido modificados

## Archivos del proyecto
* `cia_api.py`: API utilizada para cifrar, descifrar, firmar y verificar mensajes
* `chat_app.py`: contiene la lógica principal del chat y la conexión con MySQL
* `index.html`: contiene la interfaz web del chat
* `config.py`: contiene la configuración para conectarse a MySQL
* `schema.sql`: crea la base de datos y la tabla de mensajes
* `requirements.txt`: contiene las librerías necesarias para ejecutar el proyecto
* `.gitignore`: evita subir archivos innecesarios al repositorio


## Requisitos
Para ejecutar el proyecto es necesario contar con:
* Python 3.12
* MySQL Server
* MySQL Workbench
* Un navegador web


## Configurar la base de datos
Abrir MySQL Workbench y ejecutar el archivo:
`schema.sql`
Este archivo crea la base de datos `chat_seguro` y la tabla `messages`


## Configurar MySQL
Abrir el archivo `config.py` y colocar la contraseña correspondiente al usuario de MySQL en:
```python
MYSQL_PASSWORD = "TU_PASSWORD_MYSQL"
```

## Crear el entorno virtual
Abrir una terminal en la carpeta del proyecto y ejecutar:
```powershell
py -3.12 -m venv venv312
```
Después activar el entorno:
```powershell
.\venv312\Scripts\Activate.ps1
```

## Instalar las dependencias
Con el entorno virtual activo ejecutar:
```powershell
python -m pip install -r requirements.txt
```

## Iniciar la CIA API
En una terminal ejecutar:
```powershell
python -m uvicorn cia_api:app --reload --port 8000
```
La documentación de la API se puede consultar en:
`http://127.0.0.1:8000/docs`


## Iniciar el chat
Mantener abierta la terminal de la CIA API y abrir una segunda terminal
Activar nuevamente el entorno virtual y ejecutar:
```powershell
python -m uvicorn chat_app:app --reload --port 8001
```
Abrir el chat desde:
`http://127.0.0.1:8001`


## Uso del chat
El chat cuenta con dos usuarios:
* Usuario A
* Usuario B
Se pueden abrir dos pestañas del navegador y seleccionar un usuario diferente en cada una para intercambiar mensajes


## Funcionamiento
Cuando un usuario envía un mensaje:
1. El mensaje se cifra mediante la CIA API
2. Se genera una firma para comprobar su integridad
3. El mensaje cifrado y la firma se guardan en MySQL
4. El chat consulta los mensajes directamente desde la base de datos
5. El mensaje se descifra para mostrarlo al usuario
6. Inicialmente aparece como `No verificado`
7. La aplicación verifica su integridad
8. Si la verificación es correcta cambia a `Mensaje verificado`


## Base de datos
La tabla `messages` almacena:
* Remitente
* Destinatario
* Mensaje cifrado
* Firma
* Fecha y hora
El mensaje original no se guarda en texto plano dentro de MySQL


## Nota 
La CIA API genera nuevas claves cada vez que se inicia.
Si la CIA API se reinicia, los mensajes anteriores pueden dejar de descifrarse porque fueron cifrados utilizando una clave diferente.
Para realizar las pruebas se recomienda iniciar primero la CIA API, después el chat y finalmente enviar los mensajes.
