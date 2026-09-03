"""
Extracción de texto de documentos.
Devuelve una lista de tuplas (texto, página) para conservar la referencia
de página cuando es posible (requisito 7 + bonus de página).
"""
from pypdf import PdfReader
from docx import Document


def extract_pdf(path: str) -> list[tuple[str, int | None]]:
    """Extrae el texto de un PDF, página por página (páginas numeradas desde 1)."""
    reader = PdfReader(path)
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append((text, i))
    return pages


def extract_docx(path: str) -> list[tuple[str, int | None]]:
    """
    Extrae el texto de un DOCX.
    Los .docx no guardan saltos de página de forma fiable, así que
    se devuelve todo el texto con página = None.
    """
    doc = Document(path)
    text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    return [(text, None)] if text.strip() else []


def extract_text(path: str, filename: str) -> list[tuple[str, int | None]]:
    """Enruta al extractor correcto según la extensión del archivo."""
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return extract_pdf(path)
    if lower.endswith(".docx"):
        return extract_docx(path)
    raise ValueError(f"Formato no soportado: {filename}. Solo PDF y DOCX.")
