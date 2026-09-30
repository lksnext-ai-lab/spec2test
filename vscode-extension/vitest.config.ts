import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    include: ['test/**/*.test.ts'],
    coverage: { provider: 'v8', include: ['src/core/**', 'src/mcp.ts', 'src/repo.ts', 'src/docker.ts'], reporter: ['text', 'lcov'] },
  },
});
