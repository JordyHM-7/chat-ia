import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Proxy: todo lo que empiece con /api se redirige al backend (FastAPI, puerto 8000).
// Así el frontend llama a rutas relativas y no hay problemas de CORS en desarrollo.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
