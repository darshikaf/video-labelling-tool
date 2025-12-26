import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Default to localhost for local dev, Docker Compose overrides with env vars
const BACKEND_URL = process.env.VITE_BACKEND_URL || 'http://localhost:8000'
const SAM_URL = process.env.VITE_SAM_URL || 'http://localhost:8001'
const SAM2_URL = process.env.VITE_SAM2_URL || 'http://localhost:8002'

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
      // SAM2 must come before SAM to avoid prefix matching issues
      '/sam2': {
        target: SAM2_URL,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/sam2/, ''),
      },
      // Legacy SAM endpoint (only matches /sam, not /sam2)
      '^/sam(?!/2)': {
        target: SAM_URL,
        changeOrigin: true,
      },
    }
  },
  resolve: {
    alias: {
      '@': '/src',
    },
  },
})
