/**
 * Cliente de API centralizado.
 * Todas las llamadas al backend viven aquí: si mañana cambia una ruta
 * o el manejo de errores, se toca un solo archivo.
 */

async function request(url, options = {}) {
  const res = await fetch(url, options)
  if (!res.ok) {
    let detail = `Error ${res.status}`
    try {
      const body = await res.json()
      if (body.detail) detail = body.detail
    } catch {
      /* respuesta sin JSON: se mantiene el mensaje genérico */
    }
    throw new Error(detail)
  }
  return res.json()
}

export const api = {
  // Conversaciones
  listConversations: () => request('/api/conversations'),
  createConversation: () => request('/api/conversations', { method: 'POST' }),
  getConversation: (id) => request(`/api/conversations/${id}`),
  deleteConversation: (id) =>
    request(`/api/conversations/${id}`, { method: 'DELETE' }),

  // Chat
  sendMessage: (conversationId, message) =>
    request('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ conversation_id: conversationId, message }),
    }),

  // Documentos
  listDocuments: () => request('/api/documents'),
  uploadDocument: (file) => {
    const form = new FormData()
    form.append('file', file)
    return request('/api/upload', { method: 'POST', body: form })
  },
  deleteDocument: (filename) =>
    request(`/api/documents/${encodeURIComponent(filename)}`, {
      method: 'DELETE',
    }),
}
