import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// dev/preview 서버는 /api 를 FastAPI 백엔드로 프록시(같은 오리진처럼).
// 백엔드 포트는 VITE_API_PORT(기본 8781)로 조정.
const API_PORT = process.env.VITE_API_PORT || '8781'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/api': { target: `http://127.0.0.1:${API_PORT}`, changeOrigin: true } },
  },
  preview: {
    port: 4173,
    proxy: { '/api': { target: `http://127.0.0.1:${API_PORT}`, changeOrigin: true } },
  },
})
