/**
 * Barra lateral: botón de nueva conversación, historial de chats
 * y panel de documentos para el RAG.
 */
import DocumentPanel from './DocumentPanel'

export default function Sidebar({
  conversations,
  activeId,
  documents,
  onNewConversation,
  onSelectConversation,
  onDeleteConversation,
  onUpload,
  onDeleteDocument,
}) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h1 className="app-title">Chat IA</h1>
        <button className="btn-primary" onClick={onNewConversation}>
          + Nueva conversación
        </button>
      </div>

      <nav className="conversation-list">
        {conversations.length === 0 && (
          <p className="empty-hint">Aún no hay conversaciones. Crea la primera.</p>
        )}
        {conversations.map((conv) => (
          <div
            key={conv.id}
            className={`conversation-item ${conv.id === activeId ? 'active' : ''}`}
            onClick={() => onSelectConversation(conv.id)}
          >
            <span className="conversation-title">{conv.title}</span>
            <button
              className="btn-icon"
              title="Eliminar conversación"
              onClick={(e) => {
                e.stopPropagation()
                onDeleteConversation(conv.id)
              }}
            >
              ✕
            </button>
          </div>
        ))}
      </nav>

      <DocumentPanel
        documents={documents}
        onUpload={onUpload}
        onDeleteDocument={onDeleteDocument}
      />
    </aside>
  )
}
