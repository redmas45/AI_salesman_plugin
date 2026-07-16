import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '');

  return {
    base: normalizeBasePath(env.VITE_CLIENT_PANEL_BASE_PATH || '/client_panel/'),
    plugins: [react(), tailwindcss()],
    server: {
      port: 5177,
    },
  };
});

function normalizeBasePath(path: string): string {
  const trimmed = path.trim();
  if (!trimmed || trimmed === '/') return '/';
  return `/${trimmed.replace(/^\/+|\/+$/g, '')}/`;
}
