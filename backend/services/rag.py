"""
Servicio RAG (Retrieval-Augmented Generation).

Pipeline de indexación:  texto -> chunks -> embeddings -> SQLite
Pipeline de consulta:    pregunta -> embedding -> similitud coseno -> top-k chunks

Decisión técnica: para el volumen de documentos de este caso práctico,
la similitud coseno con NumPy sobre SQLite es suficiente y elimina la
dependencia de una base vectorial externa. Con miles de documentos se
migraría a ChromaDB/FAISS (solo habría que reemplazar este archivo).
"""
import re
import numpy as np
from sentence_transformers import SentenceTransformer

from database import get_db

# Modelo de embeddings multilingüe (~470MB, descarga única, corre en CPU).
# Se eligió la variante multilingüe porque los documentos y preguntas son
# en español y la variante base (all-MiniLM-L6-v2) está entrenada en inglés.
_model: SentenceTransformer | None = None

CHUNK_SIZE = 900       # caracteres por chunk
CHUNK_OVERLAP = 150    # solapamiento para no cortar ideas por la mitad
TOP_K = 4              # cuántos chunks se pasan al modelo como contexto
MIN_SIMILARITY = 0.35  # umbral bajo a propósito: la recuperación favorece recall;
                       # la precisión la aporta el modelo con la marca [DOCS]
RELATIVE_CUTOFF = 0.20 # margen bajo el mejor resultado para descartar chunks
FILENAME_BOOST = 0.15  # impulso cuando la consulta nombra el archivo

# Palabras del nombre de archivo que no aportan señal para el refuerzo léxico
_STOPWORDS = {"es", "el", "la", "de", "del", "y", "en", "un", "una", "sem"}


def get_model() -> SentenceTransformer:
    """Carga perezosa del modelo: solo se descarga/carga la primera vez."""
    global _model
    if _model is None:
        _model = SentenceTransformer(
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
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


def _filename_tokens(filename: str) -> set[str]:
    """Palabras significativas del nombre de archivo (sin extensión ni ruido)."""
    stem = filename.rsplit(".", 1)[0].lower()
    return {
        t
        for t in re.split(r"[^a-záéíóúñ0-9]+", stem)
        if len(t) >= 2 and t not in _STOPWORDS and not t.isdigit()
    }


def search_chunks(query: str) -> list[dict]:
    """
    Busca los chunks más relevantes para la consulta.
    Devuelve [{filename, page, content, score}] ordenados por similitud.
    """
    conn = get_db()
    rows = conn.execute(
        "SELECT filename, page, content, embedding FROM chunks"
    ).fetchall()
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

    # Refuerzo léxico (búsqueda híbrida): si la consulta menciona el nombre
    # de un archivo ("el cv", "el paper"), sus chunks reciben un impulso.
    # Compensa las preguntas "meta" sobre un documento, que comparten poco
    # vocabulario con su contenido y por eso puntúan bajo semánticamente.
    # Los guiones bajos se normalizan para que "cv_jordy_es" también coincida
    query_lower = query.lower().replace("_", " ")
    boost_cache: dict[str, bool] = {}
    for i, r in enumerate(rows):
        filename = r["filename"]
        if filename not in boost_cache:
            boost_cache[filename] = any(
                re.search(rf"\b{re.escape(t)}\b", query_lower)
                for t in _filename_tokens(filename)
            )
        if boost_cache[filename]:
            scores[i] += FILENAME_BOOST

    top_idx = np.argsort(scores)[::-1][:TOP_K]

    # Corte relativo: se descartan chunks notablemente peores que el mejor.
    # Evita que documentos poco relacionados "se cuelen" como fuente
    # cuando existe otro documento claramente más relevante.
    best = float(scores[top_idx[0]]) if len(top_idx) else 0.0
    cutoff = max(MIN_SIMILARITY, best - RELATIVE_CUTOFF)

    print("[RAG] query:", query[:60])
    print(
        "[RAG] top-k pre-corte:",
        [
            (rows[int(i)]["filename"], rows[int(i)]["page"], round(float(scores[i]), 3))
            for i in top_idx
        ],
    )

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

    print("[RAG] resultados:", [(r["filename"], round(r["score"], 3)) for r in results])
    return results