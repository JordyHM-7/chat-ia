/**
 * Componente raíz.
 * Mantiene todo el estado de la aplicación (conversaciones, mensajes,
 * documentos) y lo distribuye a los componentes por props.
 * Para esta escala, esto es más claro que agregar Redux o Context.
 */
import { useEffect, useState } from 'react'
import { api } from './api'
import Sidebar from './components/Sidebar'
import ChatWindow from './components/ChatWindow'
import MessageInput from './components/MessageInput'

export default function App() {
  const [conversations, setConversations] = useState([])
  const [activeId, setActiveId] = useState(null)
  const [messages, setMessages] = useState([])
  const [documents, setDocuments] = useState([])
  const [isTyping, setIsTyping] = useState(false)
  const [error, setError] = useState(null)

  // Carga inicial: historial de conversaciones y documentos indexados
  useEffect(() => {
    api.listConversations().then(setConversations).catch(showError)
    api.listDocuments().then(setDocuments).catch(showError)
  }, [])

  function showError(e) {
    setError(e.message)
    setTimeout(() => setError(null), 6000)
  }

  async function handleNewConversation() {
    try {
      const conv = await api.createConversation()
      setConversations((prev) => [conv, ...prev])
      setActiveId(conv.id)
      setMessages([])
    } catch (e) {
      showError(e)
    }
  }

  async function handleSelectConversation(id) {
    try {
      setActiveId(id)
      const conv = await api.getConversation(id)
      setMessages(conv.messages)
    } catch (e) {
      showError(e)
    }
  }

  async function handleDeleteConversation(id) {
    try {
      await api.deleteConversation(id)
      setConversations((prev) => prev.filter((c) => c.id !== id))
      if (id === activeId) {
        setActiveId(null)
        setMessages([])
      }
    } catch (e) {
      showError(e)
    }
  }

  async function handleSendMessage(text) {
    try {
      // Si no hay conversación activa, se crea una automáticamente
      let convId = activeId
      if (!convId) {
        const conv = await api.createConversation()
        setConversations((prev) => [conv, ...prev])
        setActiveId(conv.id)
        convId = conv.id
      }

      // Mostrar el mensaje del usuario de inmediato (UI optimista)
      setMessages((prev) => [...prev, { role: 'user', content: text, sources: [] }])
      setIsTyping(true)

      const reply = await api.sendMessage(convId, text)
      setMessages((prev) => [...prev, reply])

      // Refrescar la sidebar (el primer mensaje se convierte en título)
      api.listConversations().then(setConversations).catch(() => {})
    } catch (e) {
      showError(e)
    } finally {
      setIsTyping(false)
    }
  }

  async function handleUpload(file) {
    try {
      const result = await api.uploadDocument(file)
      setDocuments(await api.listDocuments())
      return result
    } catch (e) {
      showError(e)
      return null
    }
  }

  async function handleDeleteDocument(filename) {
    try {
      await api.deleteDocument(filename)
      setDocuments((prev) => prev.filter((d) => d.filename !== filename))
    } catch (e) {
      showError(e)
    }
  }

  return (
    <div className="app">
      <Sidebar
        conversations={conversations}
        activeId={activeId}
        documents={documents}
        onNewConversation={handleNewConversation}
        onSelectConversation={handleSelectConversation}
        onDeleteConversation={handleDeleteConversation}
        onUpload={handleUpload}
        onDeleteDocument={handleDeleteDocument}
      />

      <main className="chat-area">
        {error && <div className="error-banner">{error}</div>}
        <ChatWindow messages={messages} isTyping={isTyping} hasActive={activeId !== null} />
        <MessageInput onSend={handleSendMessage} disabled={isTyping} />
      </main>
    </div>
  )
}
