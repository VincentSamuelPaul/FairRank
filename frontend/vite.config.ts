import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// Same-origin in dev too: /api goes to Django, so session cookies and CSRF behave as in production.
const target = process.env.VITE_PROXY_TARGET ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': path.resolve(import.meta.dirname, 'src') } },
  test: { environment: 'jsdom', setupFiles: ['./src/test/setup.ts'], globals: false },
  server: {
    proxy: {
      '/api': { target, changeOrigin: false },
      '/admin': { target, changeOrigin: false },
    },
  },
})
