import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  define: {
    global: 'window',
  },
  resolve: {
    alias: {
      buffer: 'buffer/',
    },
  },
  build: {
    chunkSizeWarningLimit: 3000, // Increase limit to suppress warning for Plotly
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'axios', 'framer-motion'],
          plotly: ['react-plotly.js', 'plotly.js-dist-min']
        }
      }
    }
  }
})
