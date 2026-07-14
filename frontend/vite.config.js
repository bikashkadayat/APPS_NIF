import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const apiUrl = process.env.VITE_API_URL || 'http://localhost:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api/v1': {
        target: apiUrl,
        changeOrigin: true,
        secure: false,
      },
      // Uploaded media (profile photos, memo attachments) live on the backend.
      // Without this, /media/* falls through to the SPA index.html and every
      // <img src="/media/..."> renders broken.
      '/media': {
        target: apiUrl,
        changeOrigin: true,
        secure: false,
      },
    },
  },
})
