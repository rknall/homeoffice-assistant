import { execFileSync } from 'node:child_process'
import path from 'node:path'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Get git commit hash for version tracking (build-time only, no user input)
function getGitCommitHash(): string {
  try {
    return execFileSync('git', ['rev-parse', '--short', 'HEAD']).toString().trim()
  } catch {
    return 'unknown'
  }
}

export default defineConfig({
  plugins: [react()],
  define: {
    // biome-ignore lint/style/useNamingConvention: Vite convention for global constants
    __GIT_COMMIT__: JSON.stringify(getGitCommitHash()),
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
  test: {
    include: [
      'src/**/*.{test,spec}.{js,ts,tsx}',
      '../plugins/*/frontend/tests/**/*.{test,spec}.{js,ts,tsx}',
    ],
  },
})
