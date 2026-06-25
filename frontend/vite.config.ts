import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// API base URL is read at runtime from import.meta.env.VITE_API_URL (see
// vite-env.d.ts), so it isn't needed here. host:true lets the dev server be
// reachable from outside the container (Docker).
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    strictPort: true,
  },
});
