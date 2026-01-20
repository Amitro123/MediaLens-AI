import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
    server: {
        host: "::",
        port: 5173,
        proxy: {
            '/api': {
                target: 'http://127.0.0.1:8000',
                changeOrigin: true,
            },
            '/uploads': {
                target: 'http://127.0.0.1:8000',
                changeOrigin: true,
            },
        },
    },
    plugins: [react()],
    resolve: {
        alias: {
            "@": path.resolve(__dirname, "./src"),
            "\\.(css|less|sass|scss)$": path.resolve(__dirname, "./src/tests/styleMock.js"),
        },
    },
    test: {
        globals: true,
        environment: "jsdom",
        setupFiles: "./src/tests/setup.ts",
    },
}));
