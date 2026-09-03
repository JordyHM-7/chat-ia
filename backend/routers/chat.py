"""
Router de chat: el corazón de la aplicación.

Flujo de cada mensaje:
  1. Guardar el mensaje del usuario
  2. Buscar contexto relevante en los documentos
     - La búsqueda usa la pregunta + últimos mensajes
  3. Armar el prompt: system con contexto documental + TODO el historial
     de la conversación
  4. Llamar al LLM
  5. Guardar la respuesta con sus fuentes y devolverla.
"""
import json
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database import get_db
from services import llm, rag

router = APIRouter(tags=["chat"])

SYSTEM_PROMPT = (
    "Eres un asistente útil que responde en español de forma clara y concisa. "
    "Cuando se te proporcione CONTEXTO DE DOCUMENTOS, básate en él para responder "
    "y menciona de qué documento proviene la información. Si la pregunta no tiene "
    "relación con los documentos, responde con tu conocimiento general. "
    "Si el contexto no contiene la respuesta, dilo honestamente. "
    "Al final de tu respuesta, en una línea nueva, escribe exactamente [DOCS: SI] "
    "si usaste el CONTEXTO DE DOCUMENTOS para responder, o [DOCS: NO] si no lo usaste. "
    "No menciones ni expliques esta marca."
)


class ChatRequest(BaseModel):
    conversation_id: int
    message: str


@router.post("/chat")
def chat(req: ChatRequest):
    conn = get_db()

    # Validar que la conversación existe
    conv = conn.execute(
        "SELECT * FROM conversations WHERE id = ?", (req.conversation_id,)
    ).fetchone()
    if conv is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Conversación no encontrada")

    # 1. Guardar el mensaje del usuario
    conn.execute(
        "INSERT INTO messages (conversation_id, role, content) VALUES (?, 'user', ?)",
        (req.conversation_id, req.message),
    )

    # Si es el primer mensaje, usarlo como título de la conversación
    if conv["title"] == "Nueva conversación":
        title = req.message[:60] + ("…" if len(req.message) > 60 else "")
        conn.execute(
            "UPDATE conversations SET title = ? WHERE id = ?",
            (title, req.conversation_id),
        )
    conn.commit()

    # Cargar el historial completo de la conversación
    history = conn.execute(
        "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id",
        (req.conversation_id,),
    ).fetchall()

    # 2. Búsqueda RAG en dos pasadas:
    #    - Primera: solo la pregunta actual (precisión en preguntas autónomas).
    #    - Segunda: pregunta + últimos mensajes, únicamente si la primera no
    #      encontró nada — señal de pregunta referencial.
    retrieved = rag.search_chunks(req.message)
    if not retrieved and len(history) > 1:
        recent = " ".join(m["content"] for m in history[-3:])
        retrieved = rag.search_chunks(recent)

    # 3. Construir los mensajes para el LLM
    system = SYSTEM_PROMPT
    if retrieved:
        context_parts = []
        for c in retrieved:
            ref = c["filename"] + (f", página {c['page']}" if c["page"] else "")
            context_parts.append(f"[Fuente: {ref}]\n{c['content']}")
        system += "\n\nCONTEXTO DE DOCUMENTOS:\n" + "\n\n---\n\n".join(context_parts)

    llm_messages = [{"role": "system", "content": system}] + [
        {"role": m["role"], "content": m["content"]} for m in history
    ]

    # 4. Generar la respuesta
    try:
        answer = llm.generate_response(llm_messages)
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=502, detail=f"Error del proveedor de IA: {e}")

    # ¿El modelo realmente usó los documentos? Se le pide que lo declare
    # con una marca [DOCS: SI/NO] que se extrae y elimina de la respuesta.
    used_docs = True  # si no hay marca, se conserva el comportamiento anterior
    match = re.search(r"\[DOCS:\s*(SI|SÍ|NO)\]", answer, re.IGNORECASE)
    if match:
        used_docs = match.group(1).upper() != "NO"
        answer = re.sub(
            r"\s*\[DOCS:\s*(SI|SÍ|NO)\]\s*", "", answer, flags=re.IGNORECASE
        ).strip()

    if not used_docs:
        retrieved = []

    # 5. Guardar la respuesta con sus fuentes (sin duplicados)
    seen = set()
    sources = []
    for c in retrieved:
        key = (c["filename"], c["page"])
        if key not in seen:
            seen.add(key)
            sources.append({"filename": c["filename"], "page": c["page"]})

    conn.execute(
        "INSERT INTO messages (conversation_id, role, content, sources) "
        "VALUES (?, 'assistant', ?, ?)",
        (req.conversation_id, answer, json.dumps(sources) if sources else None),
    )
    conn.commit()
    conn.close()

    return {"role": "assistant", "content": answer, "sources": sources}
