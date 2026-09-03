/**
 * Un mensaje del chat. Los del asistente se renderizan como Markdown
 * (los modelos responden con negritas, listas, código, etc.) y muestran
 * sus fuentes documentales cuando la respuesta usó RAG.
 */
import ReactMarkdown from "react-markdown";
import SourceBadge from "./SourceBadge";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";

export default function MessageBubble({ message }) {
  const isUser = message.role === "user";

  return (
    <div className={`message ${isUser ? "user" : "assistant"}`}>
      <div className="bubble">
        {isUser ? (
          message.content
        ) : (
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeRaw]}
          >
            {message.content}
          </ReactMarkdown>
        )}
      </div>

      {!isUser && message.sources?.length > 0 && (
        <div className="sources">
          {message.sources.map((src, i) => (
            <SourceBadge key={i} source={src} />
          ))}
        </div>
      )}
    </div>
  );
}
