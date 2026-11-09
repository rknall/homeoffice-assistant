import { execFileSync } from 'node:child_process'
import path from 'node:path'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'
import pkg from './package.json'

// Get git commit hash for version tracking (build-time only, no user input)
function getGitCommitHash(): string {
  try {
    return execFileSync('git', ['rev-parse', '--short', 'HEAD']).toString().trim()
  } catch (error) {
    if (process.env.NODE_ENV !== 'production') {
      const message = error instanceof Error ? error.message : String(error)
      console.warn('[vite] Failed to determine git commit hash:', message)
    }
    return 'unknown'
  }
}

export default defineConfig({
  plugins: [react()],
  define: {
    // biome-ignore lint/style/useNamingConvention: Vite convention for global constants
    __APP_VERSION__: JSON.stringify(pkg.version),
    // biome-ignore lint/style/useNamingConvention: Vite convention for global constants
    __GIT_COMMIT__: JSON.stringify(getGitCommitHash()),
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      // Plugin sources and tests live outside this package; resolve their bare
      // imports from its node_modules.
      react: path.resolve(__dirname, './node_modules/react'),
      '@testing-library/react': path.resolve(__dirname, './node_modules/@testing-library/react'),
      '@testing-library/user-event': path.resolve(
        __dirname,
        './node_modules/@testing-library/user-event',
      ),
    },
  },
  server: {
    // Plugin tests under ../plugins are served from outside this package
    fs: { allow: ['..'] },
    proxy: {
      '/api': 'http://localhost:8000',
      // Uploaded avatars are served by the backend from static/avatars
      '/avatars': 'http://localhost:8000',
    },
  },
  test: {
    include: [
      'src/**/*.{test,spec}.{js,ts,tsx}',
      '../plugins/*/frontend/tests/**/*.{test,spec}.{js,ts,tsx}',
    ],
  },
})
