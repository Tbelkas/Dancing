import { defineConfig } from 'vitest/config';

// Unit tests for framework-free logic (pure utils). Components that need Angular's
// TestBed are out of scope here; this keeps the suite fast and headless for CI.
export default defineConfig({
  test: {
    include: ['src/**/*.spec.ts'],
    environment: 'node',
  },
});
