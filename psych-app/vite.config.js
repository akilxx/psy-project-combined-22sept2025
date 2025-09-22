//Psych-app


import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,          // listen on 0.0.0.0 so ngrok can reach it
    port: 5173,          // your Vite port
    allowedHosts: ['.trycloudflare.com', 'localhost', '127.0.0.1',  'app.investmentlab.org'],   // allow every *.ngrok‑free.app sub‑domain
    // If you use a reserved/static domain, you can list it directly:
    // allowedHosts: ['my‑vite.ngrok.app'],
    hmr: {
      host: 'app.investmentlab.org',
      protocol: 'wss',
      clientPort: 443
    }
  },
})
