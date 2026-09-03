# Chat IA con RAG

Aplicación web de chat con Inteligencia Artificial que permite mantener conversaciones con historial persistente y consultar el contenido de documentos (PDF y DOCX) cargados por el usuario, indicando las fuentes de cada respuesta.

Desarrollada como caso práctico para la pasantía de Desarrollo con IA.

## Funcionalidades

- Chat con IA con memoria conversacional dentro de cada conversación
- Historial de conversaciones persistente (sobrevive recargas y reinicios)
- Carga e indexación de documentos PDF y DOCX
- Consulta de documentos mediante RAG (Retrieval-Augmented Generation)
- Indicación de fuentes: nombre del archivo y página cuando está disponible
- Indicador de escritura ("typing indicator") y renderizado Markdown de las respuestas (incluyendo tablas)
- Creación automática de conversación al escribir sin chat activo, con título tomado del primer mensaje

## Arquitectura

```
┌─────────────────────┐         ┌──────────────────────────────────────┐
│  Frontend (React)   │  HTTP   │           Backend (FastAPI)          │
│                     │ ─────►  │                                      │
│  - Interacción UI   │  JSON   │  routers/   capa HTTP                │
│  - api.js           │         │  services/  lógica (LLM, RAG)        │
│    (cliente único)  │         │  database   SQLite                   │
└─────────────────────┘         └──────┬──────────────┬────────────────┘
                                       │              │
                                ┌──────▼─────┐  ┌─────▼──────────────┐
                                │   SQLite   │  │  Groq API (LLM)    │
                                │ conversac. │  │  gpt-oss-120b      │
                                │ mensajes   │  │  (tier gratuito)   │
                                │ chunks+emb │  └────────────────────┘
                                └────────────┘
```

Arquitectura en capas con separación estricta de responsabilidades:

- **`routers/`** — capa HTTP: recibe requests, valida y responde. No contiene lógica de negocio.
- **`services/`** — lógica de la aplicación: `llm.py` (proveedor de IA), `rag.py` (chunking, embeddings, búsqueda), `extractors.py` (lectura de PDF/DOCX). No conocen FastAPI ni HTTP.
- **`database.py`** — capa de datos (SQLite).

Esta estructura respeta la regla de dependencias de Clean Architecture (la lógica no depende de los detalles externos) sin la sobrecarga de una implementación completa con puertos e interfaces, que sería desproporcionada para este alcance. Cambiar de proveedor de IA o de mecanismo de búsqueda vectorial implica modificar un solo archivo.

## Stack y justificación de decisiones

| Componente | Elección | Justificación |
|---|---|---|
| Backend | Python + FastAPI | Ecosistema natural de las librerías de IA/RAG; validación automática con Pydantic; documentación interactiva en `/docs` |
| Frontend | React + Vite | Componentización clara; estado centralizado en `App.jsx` con props (Redux sería sobre-ingeniería para esta escala) |
| Persistencia | SQLite | Cero configuración, transaccional, suficiente para la escala del caso; migrar a PostgreSQL solo cambia la capa de datos |
| LLM | Groq API — `openai/gpt-oss-120b` | API gratuita (requisito: sin APIs de pago), muy baja latencia; el modelo es configurable por variable de entorno porque Groq depreca modelos con frecuencia |
| Embeddings | sentence-transformers `all-MiniLM-L6-v2` | Local y gratuito, corre en CPU, calidad suficiente para recuperación semántica |
| Búsqueda vectorial | Similitud coseno con NumPy | Para el volumen de este caso (< miles de chunks) una base vectorial externa no aporta; con más escala se migraría a ChromaDB/FAISS tocando solo `services/rag.py` |
| Extracción | pypdf + python-docx | Estándar; pypdf conserva el número de página para la atribución de fuentes |

## Decisiones de diseño del RAG

- **Chunking:** fragmentos de ~900 caracteres con 150 de solapamiento, para no cortar ideas en los bordes.
- **Recuperación:** top 4 chunks por similitud coseno, con doble filtro: umbral absoluto (0.30) y corte relativo al mejor resultado, que descarta documentos notablemente menos relevantes que el mejor encontrado.
- **Memoria conversacional + RAG:** la búsqueda se hace con la pregunta actual más los últimos mensajes de la conversación. Así, una pregunta de seguimiento como "¿y por qué ese límite?" recupera los chunks correctos aunque no repita el tema. Además, el historial completo de la conversación se envía al modelo en cada turno, por lo que las respuestas previas (incluidas las generadas con RAG) forman parte del contexto.
- **Atribución de fuentes:** las fuentes (archivo y página) se devuelven al frontend y se **persisten junto al mensaje**, de modo que siguen visibles al reabrir conversaciones antiguas. El chat funciona igualmente sin documentos: si ningún chunk supera los filtros, el modelo responde con conocimiento general y no se muestra fuente.

## Instalación y ejecución

Requisitos: Python 3.10+, Node 18+, y una API key gratuita de Groq ([console.groq.com](https://console.groq.com) → API Keys, no requiere tarjeta).

### Backend

```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

Crear el archivo `.env` (puede copiarse de `.env.example`):

```
GROQ_API_KEY=gsk_tu_clave
GROQ_MODEL=openai/gpt-oss-120b
```

Arrancar:

```bash
uvicorn main:app --reload
```

La API queda en `http://localhost:8000` (documentación interactiva en `/docs`).

### Frontend

En otra terminal:

```bash
cd frontend
npm install
npm run dev
```

La aplicación queda en `http://localhost:5173`. El proxy de Vite redirige `/api` al backend, por lo que no hay que configurar CORS ni URLs.

Nota: la primera carga de un documento tarda unos segundos adicionales porque descarga el modelo de embeddings (una única vez).

## Uso

1. Escribir un mensaje (se crea una conversación automáticamente) o pulsar "Nueva conversación".
2. Para consultar documentos: "Subir PDF o DOCX" en el panel inferior de la barra lateral, esperar el estado "listo (N fragmentos)" y preguntar sobre su contenido.
3. Las respuestas basadas en documentos muestran un chip con el archivo de origen y la página cuando está disponible.
4. Las conversaciones anteriores se recuperan desde la barra lateral, con sus fuentes intactas.

## Limitaciones conocidas

- **Atribución de fuentes por recuperación, no por uso:** los chips muestran todos los documentos consultados durante la recuperación, que no siempre coinciden exactamente con los que el modelo terminó usando. Cuando dos documentos son temáticamente cercanos, ambos pueden aparecer como fuente. Se mitiga con el corte de similitud relativo; con más tiempo se implementaría re-ranking o el cruce entre los chunks recuperados y las citas del propio modelo.
- **DOCX sin número de página:** el formato no almacena saltos de página de forma fiable, por lo que la fuente indica solo el archivo (el enunciado lo contempla: "página, sección o referencia equivalente cuando sea posible").
- **PDFs escaneados:** no se aplica OCR; si un PDF no contiene texto extraíble, se informa al usuario con un error claro.
- **Sin autenticación:** todos los usuarios comparten conversaciones y documentos, acorde al alcance del caso.

## Posibles mejoras

- Streaming de respuestas (SSE) con efecto de escritura progresiva
- Fuentes clickeables que abran el documento en la página citada
- Re-ranking de chunks con un cross-encoder para mayor precisión
- Autenticación y espacios por usuario
