"""
Capa de datos (SQLite).
Tres tablas:
  - conversations: cada chat que el usuario crea
  - messages: mensajes de cada conversación (con fuentes en JSON si aplica)
  - chunks: fragmentos de los documentos subidos, con su embedding serializado
"""
import sqlite3

DB_PATH = "chat.db"


def get_db() -> sqlite3.Connection:
    """
    Devuelve una conexión a SQLite.
    check_same_thread=False permite usarla desde los workers de FastAPI.
    row_factory hace que las filas se comporten como diccionarios.
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Crea las tablas si no existen. Se llama una vez al arrancar la app."""
    conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL DEFAULT 'Nueva conversación',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL REFERENCES conversations(id),
            role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
            content TEXT NOT NULL,
            sources TEXT,                -- JSON: [{"filename": ..., "page": ...}]
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            page INTEGER,                -- NULL para DOCX (no tienen páginas fiables)
            content TEXT NOT NULL,
            embedding BLOB NOT NULL      -- vector float32 serializado con numpy
        );
        """
    )
    conn.commit()
    conn.close()
