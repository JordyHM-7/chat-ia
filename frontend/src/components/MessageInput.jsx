/**
 * Caja de entrada: Enter envía, Shift+Enter hace salto de línea.
 * Se deshabilita mientras el asistente está respondiendo.
 */
import { useState } from 'react'

export default function MessageInput({ onSend, disabled }) {
  const [text, setText] = useState('')

  function send() {
    const trimmed = text.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setText('')
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <div className="input-bar">
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Escribe tu mensaje…"
        rows={1}
        disabled={disabled}
      />
      <button className="btn-primary" onClick={send} disabled={disabled || !text.trim()}>
        Enviar
      </button>
    </div>
  )
}
