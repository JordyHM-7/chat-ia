"""
Servicio RAG (Retrieval-Augmented Generation).

Pipeline de indexación:  texto -> chunks -> embeddings -> SQLite
Pipeline de consulta:    pregunta -> embedding -> similitud coseno -> top-k chunks

Decisión técnica: para el volumen de documentos de este caso práctico,
la similitud coseno con NumPy sobre SQLite es suficiente y elimina la
dependencia de una base vectorial externa. Con miles de documentos se
migraría a ChromaDB/FAISS (solo habría que reemplazar este archivo).
"""
import numpy as np
from sentence_transformers import SentenceTransformer

from database import get_db

# Modelo de embeddings: pequeño (~90MB), multilingüe razonable, corre en CPU.
_model: SentenceTransformer | None = None

CHUNK_SIZE = 900      # caracteres por chunk
CHUNK_OVERLAP = 150   # solapamiento para no cortar ideas por la mitad
TOP_K = 4             # cuántos chunks se pasan al modelo como contexto
MIN_SIMILARITY = 0.30 # umbral: debajo de esto se considera irrelevante


def get_model() -> SentenceTransformer:
    """Carga perezosa del modelo: solo se descarga/carga la primera vez."""
    global _model
    if _model is None:
        _model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _model


def chunk_text(text: str) -> list[str]:
    """Divide el texto en fragmentos con solapamiento."""
    text = " ".join(text.split())  # normalizar espacios y saltos de línea
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunks.append(text[start:end])
        start = end - CHUNK_OVERLAP
    return chunks


def index_document(filename: str, pages: list[tuple[str, int | None]]) -> int:
    """
    Indexa un documento: trocea cada página, calcula embeddings y guarda todo.
    Devuelve la cantidad de chunks creados.
    """
    conn = get_db()
    # Si el archivo ya estaba indexado, se reemplaza (permite re-subir)
    conn.execute("DELETE FROM chunks WHERE filename = ?", (filename,))

    all_chunks: list[tuple[str, int | None]] = []
    for text, page in pages:
        for chunk in chunk_text(text):
            all_chunks.append((chunk, page))

    if not all_chunks:
        conn.commit()
        conn.close()
        return 0

    # Calcular todos los embeddings en un solo batch (mucho más rápido)
    embeddings = get_model().encode([c for c, _ in all_chunks])

    for (content, page), emb in zip(all_chunks, embeddings):
        conn.execute(
            "INSERT INTO chunks (filename, page, content, embedding) VALUES (?, ?, ?, ?)",
            (filename, page, content, np.asarray(emb, dtype=np.float32).tobytes()),
        )
    conn.commit()
    conn.close()
    return len(all_chunks)


def search_chunks(query: str) -> list[dict]:
    """
    Busca los chunks más relevantes para la consulta.
    Devuelve [{filename, page, content, score}] ordenados por similitud.
    """
    conn = get_db()
    rows = conn.execute("SELECT filename, page, content, embedding FROM chunks").fetchall()
    conn.close()
    if not rows:
        return []

    query_emb = np.asarray(get_model().encode([query])[0], dtype=np.float32)

    # Matriz (n_chunks x dim) reconstruida desde los blobs
    matrix = np.vstack([np.frombuffer(r["embedding"], dtype=np.float32) for r in rows])

    # Similitud coseno vectorizada
    scores = matrix @ query_emb / (
        np.linalg.norm(matrix, axis=1) * np.linalg.norm(query_emb) + 1e-10
    )

    top_idx = np.argsort(scores)[::-1][:TOP_K]

    # Corte relativo: se descartan chunks notablemente peores que el mejor.
    # Evita que documentos poco relacionados "se cuelen" como fuente
    # cuando existe otro documento claramente más relevante.
    best = float(scores[top_idx[0]]) if len(top_idx) else 0.0
    cutoff = max(MIN_SIMILARITY, best - 0.12)

    results = []
    for i in top_idx:
        if scores[i] >= cutoff:
            r = rows[int(i)]
            results.append(
                {
                    "filename": r["filename"],
                    "page": r["page"],
                    "content": r["content"],
                    "score": float(scores[i]),
                }
            )
    return results
