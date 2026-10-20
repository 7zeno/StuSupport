import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    // In dev, forward API calls to FastAPI so no CORS setup is needed.
    proxy: { "/api": "http://localhost:8000" },
  },
});
