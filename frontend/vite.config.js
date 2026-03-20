import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    headers: {
      // Required to bypass ngrok browser warning inside Google Meet iframe
      'ngrok-skip-browser-warning': 'true',
      // Required for Google Meet iframe embedding
      'X-Frame-Options': 'ALLOWALL',
    }
  }
})