/**
 * Chip que identifica la fuente documental de una respuesta:
 * nombre del archivo y página cuando está disponible (requisito 7 + bonus).
 */
export default function SourceBadge({ source }) {
  return (
    <span className="source-badge" title={`Fuente: ${source.filename}`}>
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
      </svg>
      {source.filename}
      {source.page ? ` · pág. ${source.page}` : ''}
    </span>
  )
}
