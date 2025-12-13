import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Use Docker service names when running in container, localhost for local dev
const BACKEND_URL = process.env.VITE_BACKEND_URL || 'http://backend:8000'
const SAM_URL = process.env.VITE_SAM_URL || 'http://sam-service:8001'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    watch: {
      // Enable polling for Docker volume mounts (required for Linux/macOS compatibility)
      usePolling: true,
      interval: 1000,
    },
    proxy: {
      '/api': {
        target: BACKEND_URL,
        changeOrigin: true,
      },
      '/sam': {
        target: SAM_URL,
        changeOrigin: true,
      }
    }
  },
  resolve: {
    alias: {
      '@': '/src',
    },
  },
})
