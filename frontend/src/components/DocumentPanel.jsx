/**
 * Panel de documentos (parte inferior de la sidebar).
 * Permite subir PDF/DOCX para el RAG y ver/eliminar los ya indexados.
 */
import { useRef, useState } from 'react'

export default function DocumentPanel({ documents, onUpload, onDeleteDocument }) {
  const inputRef = useRef(null)
  const [uploading, setUploading] = useState(false)
  const [status, setStatus] = useState(null)

  async function handleFileChange(e) {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    setStatus(`Indexando ${file.name}…`)
    const result = await onUpload(file)
    setUploading(false)
    setStatus(result ? `${file.name} listo (${result.chunks} fragmentos)` : null)
    setTimeout(() => setStatus(null), 5000)
    e.target.value = '' // permite volver a subir el mismo archivo
  }

  return (
    <section className="document-panel">
      <div className="document-panel-header">
        <h2>Documentos</h2>
        <button
          className="btn-secondary"
          disabled={uploading}
          onClick={() => inputRef.current?.click()}
        >
          {uploading ? 'Indexando…' : 'Subir PDF o DOCX'}
        </button>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx"
          hidden
          onChange={handleFileChange}
        />
      </div>

      {status && <p className="upload-status">{status}</p>}

      <ul className="document-list">
        {documents.length === 0 && (
          <li className="empty-hint">
            Sube un documento y pregúntale sobre su contenido.
          </li>
        )}
        {documents.map((doc) => (
          <li key={doc.filename} className="document-item">
            <span className="document-name" title={doc.filename}>
              {doc.filename}
            </span>
            <button
              className="btn-icon"
              title="Quitar del índice"
              onClick={() => onDeleteDocument(doc.filename)}
            >
              ✕
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}
