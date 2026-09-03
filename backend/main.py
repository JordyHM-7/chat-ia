"""
Punto de entrada de la aplicación.
Solo se encarga de: crear la app, configurar CORS y registrar los routers.
Toda la lógica vive en routers/ y services/.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from routers import conversations, chat, documents

app = FastAPI(title="Chat IA con RAG", version="1.0")

# CORS: permite que el frontend (Vite, puerto 5173) hable con el backend.
# El proxy de Vite ya lo resuelve en desarrollo, pero esto evita sorpresas.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Crear las tablas de SQLite si no existen (se ejecuta al arrancar)
init_db()

# Registro de rutas: todas cuelgan de /api
app.include_router(conversations.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(documents.router, prefix="/api")


@app.get("/api/health")
def health():
    """Endpoint simple para verificar que el backend está vivo."""
    return {"status": "ok"}
