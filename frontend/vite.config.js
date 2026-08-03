import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Forward API calls to Django so the browser sees everything as
      // same-origin (localhost:5173) — this means Django's session cookie
      // and CSRF protection work normally with zero CORS configuration.
      '/api': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
      },
      // Listing photos are served by Django too (MEDIA_URL), so proxy
      // those as well or images referenced by absolute URL will 404
      // when the frontend runs on a different port than Django.
      '/media': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
      },
    },
  },
})