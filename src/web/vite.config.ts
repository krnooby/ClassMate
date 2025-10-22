import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',  // 모든 네트워크 인터페이스에서 접근 허용
    port: 5173,       // 포트 명시
    strictPort: false, // 포트가 사용중이면 다른 포트 사용
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
})
