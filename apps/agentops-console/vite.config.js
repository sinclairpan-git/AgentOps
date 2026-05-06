import { defineConfig } from "vite";

export default defineConfig({
  resolve: {
    alias: {
      vue: "vue/dist/vue.esm.js"
    }
  },
  server: {
    host: "127.0.0.1",
    port: 5173
  },
  preview: {
    host: "127.0.0.1",
    port: 4173
  }
});
