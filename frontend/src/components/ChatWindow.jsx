/**
 * Área de mensajes: renderiza la conversación, el estado vacío,
 * el indicador de "escribiendo…" y hace scroll automático al final.
 */
import { useEffect, useRef } from 'react'
import MessageBubble from './MessageBubble'

export default function ChatWindow({ messages, isTyping, hasActive }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  if (!hasActive && messages.length === 0) {
    return (
      <div className="chat-window">
        <div className="welcome">
          <h2>¿En qué te puedo ayudar?</h2>
          <p>
            Escribe un mensaje para empezar, o sube un PDF o DOCX en el panel
            de documentos y pregúntale sobre su contenido. Las respuestas
            basadas en tus documentos mostrarán su fuente.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="chat-window">
      {messages.map((msg, i) => (
        <MessageBubble key={i} message={msg} />
      ))}

      {isTyping && (
        <div className="message assistant">
          <div className="bubble typing">
            <span className="dot" />
            <span className="dot" />
            <span className="dot" />
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  )
}
