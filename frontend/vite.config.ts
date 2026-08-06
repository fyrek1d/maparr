import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          'react': ['react', 'react-dom'],
          'leaflet': ['leaflet', 'leaflet-measure'],
          'utils': ['clsx', 'date-fns', 'zustand'],
        },
      },
    },
  },
  resolve: {
    alias: {
      '@': '/src',
    },
  },
})