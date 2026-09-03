"""
Router de conversaciones.
Cubre: crear conversación nueva, listar el historial y recuperar
los mensajes de una conversación anterior (requisitos 1 y 4).
"""
import json

from fastapi import APIRouter, HTTPException

from database import get_db

router = APIRouter(tags=["conversations"])


@router.post("/conversations")
def create_conversation():
    """Crea una conversación vacía y devuelve su id."""
    conn = get_db()
    cursor = conn.execute("INSERT INTO conversations DEFAULT VALUES")
    conn.commit()
    conv_id = cursor.lastrowid
    row = conn.execute(
        "SELECT * FROM conversations WHERE id = ?", (conv_id,)
    ).fetchone()
    conn.close()
    return dict(row)


@router.get("/conversations")
def list_conversations():
    """Lista todas las conversaciones, la más reciente primero (para la sidebar)."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM conversations ORDER BY created_at DESC, id DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/conversations/{conv_id}")
def get_conversation(conv_id: int):
    """Devuelve una conversación con todos sus mensajes (y sus fuentes)."""
    conn = get_db()
    conv = conn.execute(
        "SELECT * FROM conversations WHERE id = ?", (conv_id,)
    ).fetchone()
    if conv is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Conversación no encontrada")

    rows = conn.execute(
        "SELECT id, role, content, sources, created_at FROM messages "
        "WHERE conversation_id = ? ORDER BY id",
        (conv_id,),
    ).fetchall()
    conn.close()

    messages = []
    for r in rows:
        msg = dict(r)
        msg["sources"] = json.loads(msg["sources"]) if msg["sources"] else []
        messages.append(msg)

    return {**dict(conv), "messages": messages}


@router.delete("/conversations/{conv_id}")
def delete_conversation(conv_id: int):
    """Elimina una conversación y sus mensajes."""
    conn = get_db()
    conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
    conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
    conn.commit()
    conn.close()
    return {"deleted": conv_id}
