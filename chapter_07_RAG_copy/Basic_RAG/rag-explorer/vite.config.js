import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const API = process.env.API_URL || 'http://localhost:8787'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5175,
    open: true,
    proxy: {
      // Same-origin /api calls are forwarded to the Express backend.
      '/api': { target: API, changeOrigin: true },
    },
  },
})
