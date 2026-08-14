-- ============================================================
-- BASE DE DATOS DEL CHAT SEGURO
-- ============================================================

CREATE DATABASE IF NOT EXISTS chat_seguro
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE chat_seguro;

CREATE TABLE IF NOT EXISTS messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sender VARCHAR(100) NOT NULL,
    receiver VARCHAR(100) NOT NULL,
    ciphertext TEXT NOT NULL,
    signature VARCHAR(255) NOT NULL,
    timestamp DATETIME NOT NULL
);

-- Puedes ejecutar esta consulta después para comprobar los mensajes:
-- SELECT * FROM messages;
