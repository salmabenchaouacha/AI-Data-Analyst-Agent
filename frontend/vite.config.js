import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// /api is proxied to FastAPI so the frontend never hard-codes the backend URL
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://localhost:8000" } },
});
