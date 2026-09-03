"""
Servicio LLM.
Toda la comunicación con el proveedor de IA vive aquí: cambiar de Groq a
Ollama u otro proveedor solo requiere modificar este archivo.

Groq expone una API compatible con OpenAI, gratuita (con límites de tasa).
"""
import os

import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")


def generate_response(messages: list[dict]) -> str:
    """
    Envía la lista de mensajes [{role, content}, ...] al modelo
    y devuelve el texto de la respuesta.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Falta GROQ_API_KEY en el archivo .env "
            "(consíguela gratis en console.groq.com)"
        )

    response = requests.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": MODEL,
            "messages": messages,
            "temperature": 0.4,   # bajo: respuestas más fieles al contexto RAG
            "max_tokens": 1024,
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]
