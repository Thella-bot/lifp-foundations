import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      workbox: {
        // Cache API responses for 24 hours
        runtimeCaching: [
          {
            urlPattern: /\/v1\/score/,
            handler: "NetworkFirst",
            options: {
              cacheName: "score-cache",
              expiration: { maxAgeSeconds: 86400 },
            },
          },
          {
            urlPattern: /\/v1\/offers/,
            handler: "NetworkFirst",
            options: {
              cacheName: "offers-cache",
              expiration: { maxAgeSeconds: 86400 },
            },
          },
        ],
        globPatterns: ["**/*.{js,css,html,ico,png,svg}"],
      },
      manifest: {
        name: "LIFP — Lesotho Inclusive Finance Platform",
        short_name: "LIFP",
        description: "Access credit, track finances, and build your credit score.",
        theme_color: "#1F3864",
        background_color: "#f5f7fa",
        display: "standalone",
        start_url: "/",
        icons: [
          { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
        ],
      },
    }),
  ],
  server: {
    port: 5173,
    proxy: {
      "/api/acse":     { target: "http://localhost:8001", rewrite: (p) => p.replace(/^\/api\/acse/, "") },
      "/api/identity": { target: "http://localhost:8002", rewrite: (p) => p.replace(/^\/api\/identity/, "") },
    },
  },
});
