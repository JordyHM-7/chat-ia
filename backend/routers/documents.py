"""
Router de documentos.
Cubre la carga de PDF/DOCX y su indexación para RAG (requisito 6).
"""
import os

from fastapi import APIRouter, HTTPException, UploadFile

from database import get_db
from services import extractors, rag

router = APIRouter(tags=["documents"])

UPLOAD_DIR = "uploads"
ALLOWED_EXTENSIONS = (".pdf", ".docx")
MAX_SIZE_MB = 25


@router.post("/upload")
async def upload_document(file: UploadFile):
    """Recibe un PDF o DOCX, extrae su texto y lo indexa para RAG."""
    if not file.filename or not file.filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=400, detail="Solo se aceptan archivos PDF y DOCX"
        )

    content = await file.read()
    if len(content) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=400, detail=f"El archivo supera el límite de {MAX_SIZE_MB} MB"
        )

    # Guardar el archivo en disco
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    path = os.path.join(UPLOAD_DIR, os.path.basename(file.filename))
    with open(path, "wb") as f:
        f.write(content)

    # Extraer texto e indexar
    try:
        pages = extractors.extract_text(path, file.filename)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"No se pudo leer el archivo: {e}")

    if not pages:
        raise HTTPException(
            status_code=422,
            detail="No se encontró texto en el documento (¿es un PDF escaneado?)",
        )

    num_chunks = rag.index_document(file.filename, pages)
    return {"filename": file.filename, "chunks": num_chunks, "status": "indexado"}


@router.get("/documents")
def list_documents():
    """Lista los documentos indexados con su cantidad de chunks."""
    conn = get_db()
    rows = conn.execute(
        "SELECT filename, COUNT(*) as chunks FROM chunks GROUP BY filename"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.delete("/documents/{filename}")
def delete_document(filename: str):
    """Elimina un documento del índice RAG (y su archivo en disco)."""
    conn = get_db()
    cursor = conn.execute("DELETE FROM chunks WHERE filename = ?", (filename,))
    conn.commit()
    conn.close()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    path = os.path.join(UPLOAD_DIR, os.path.basename(filename))
    if os.path.exists(path):
        os.remove(path)
    return {"deleted": filename}
